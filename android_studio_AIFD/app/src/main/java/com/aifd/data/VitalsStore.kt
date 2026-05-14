package com.aifd.data

import android.content.Context
import android.util.Log
import androidx.core.content.edit

/**
 * Stores and aggregates HR / SpO2 readings for live, 1-hour, and 24-hour views.
 *
 * Memory model:
 *  - liveBuffer  : raw readings within the last 25 seconds (in-memory only)
 *  - fiveMinBuckets : 12 buckets × 5 min = 1 h of aggregated data
 *  - hourlyBuckets  : 24 buckets × 1 h  = 24 h of aggregated data
 *
 * SharedPreferences keys (compact CSV, never grows beyond ~2 KB):
 *  - "vitals_5min"  : "ts,hrSum,hrCount,spo2Sum,spo2Count|..."
 *  - "vitals_1h"    : same format, 24 entries
 */
class VitalsStore(private val context: Context) {

    companion object {
        private const val TAG = "VitalsStore"
        private const val PREFS = "aifd_prefs"
        private const val KEY_5MIN = "vitals_5min"
        private const val KEY_1H   = "vitals_1h"

        const val LIVE_WINDOW_MS = 25_000L         // 25 seconds
        const val BUCKET_5MIN_MS = 5 * 60_000L    // 5 minutes
        const val BUCKET_1H_MS   = 60 * 60_000L   // 1 hour
        const val BUCKETS_1H     = 12              // 12 × 5 min = 60 min
        const val BUCKETS_24H    = 24              // 24 × 1 h  = 24 h
    }

    private data class RawPoint(val ts: Long, val hr: Int, val spo2: Int)

    private data class Bucket(
        val startMs: Long,
        var hrSum: Long = 0,
        var hrCount: Int = 0,
        var spo2Sum: Long = 0,
        var spo2Count: Int = 0
    ) {
        fun hrAvg()   = if (hrCount   > 0) (hrSum   / hrCount).toInt()   else 0
        fun spo2Avg() = if (spo2Count > 0) (spo2Sum / spo2Count).toInt() else 0
        fun serialize() = "$startMs,$hrSum,$hrCount,$spo2Sum,$spo2Count"

        companion object {
            fun deserialize(s: String): Bucket? = try {
                val p = s.split(",")
                Bucket(p[0].toLong(), p[1].toLong(), p[2].toInt(), p[3].toLong(), p[4].toInt())
            } catch (_: Exception) { null }
        }
    }

    // In-memory state
    private val liveBuffer      = ArrayDeque<RawPoint>()
    private val fiveMinBuckets  = LinkedHashMap<Long, Bucket>()
    private val hourlyBuckets   = LinkedHashMap<Long, Bucket>()

    // Throttle SharedPreferences writes to once per 30s
    private var lastSaveMs = 0L

    init {
        loadFromPrefs()
    }

    // ── Public API ────────────────────────────────────────────────────────

    fun addReading(hr: Int, spo2: Int) {
        val now = System.currentTimeMillis()
        val validHR   = if (hr   in 30..220) hr   else 0
        val validSpo2 = if (spo2 in 50..100) spo2 else 0
        if (validHR == 0 && validSpo2 == 0) return

        // Live buffer — keep only last 25 s
        liveBuffer.addLast(RawPoint(now, validHR, validSpo2))
        val cutoffLive = now - LIVE_WINDOW_MS
        while (liveBuffer.isNotEmpty() && liveBuffer.first().ts < cutoffLive) {
            liveBuffer.removeFirst()
        }

        // 5-min bucket
        val key5 = (now / BUCKET_5MIN_MS) * BUCKET_5MIN_MS
        val b5 = fiveMinBuckets.getOrPut(key5) { Bucket(key5) }
        if (validHR   > 0) { b5.hrSum   += validHR;   b5.hrCount++   }
        if (validSpo2 > 0) { b5.spo2Sum += validSpo2; b5.spo2Count++ }
        trimBuckets(fiveMinBuckets, BUCKETS_1H)

        // Hourly bucket
        val keyH = (now / BUCKET_1H_MS) * BUCKET_1H_MS
        val bH = hourlyBuckets.getOrPut(keyH) { Bucket(keyH) }
        if (validHR   > 0) { bH.hrSum   += validHR;   bH.hrCount++   }
        if (validSpo2 > 0) { bH.spo2Sum += validSpo2; bH.spo2Count++ }
        // Remove buckets older than 24 h
        val cutoff24 = now - BUCKETS_24H * BUCKET_1H_MS
        hourlyBuckets.keys.filter { it < cutoff24 }.forEach { hourlyBuckets.remove(it) }

        // Throttled save
        if (now - lastSaveMs > 30_000L) {
            saveToPrefs()
            lastSaveMs = now
        }
    }

    /** Max HR in the last 25 seconds, 0 if no data. */
    fun getLiveHR(): Int =
        liveBuffer.filter { it.hr > 0 }.maxOfOrNull { it.hr } ?: 0

    /** Max SpO2 in the last 25 seconds, 0 if no data. */
    fun getLiveSpO2(): Int =
        liveBuffer.filter { it.spo2 > 0 }.maxOfOrNull { it.spo2 } ?: 0

    /**
     * Returns 12 data points (one per 5-minute slot) for the past hour.
     * Slots with no data return 0 (safe, no crash).
     */
    fun get1hChart(isHR: Boolean): List<Int> {
        val now = System.currentTimeMillis()
        val currentBucket = (now / BUCKET_5MIN_MS) * BUCKET_5MIN_MS
        return (0 until BUCKETS_1H).map { i ->
            val slotStart = currentBucket - (BUCKETS_1H - 1 - i) * BUCKET_5MIN_MS
            val b = fiveMinBuckets[slotStart]
            if (isHR) b?.hrAvg() ?: 0 else b?.spo2Avg() ?: 0
        }
    }

    /**
     * Returns 24 data points (one per hour) for the past 24 hours.
     * Slots with no data return 0.
     */
    fun get24hChart(isHR: Boolean): List<Int> {
        val now = System.currentTimeMillis()
        val currentBucket = (now / BUCKET_1H_MS) * BUCKET_1H_MS
        return (0 until BUCKETS_24H).map { i ->
            val slotStart = currentBucket - (BUCKETS_24H - 1 - i) * BUCKET_1H_MS
            val b = hourlyBuckets[slotStart]
            if (isHR) b?.hrAvg() ?: 0 else b?.spo2Avg() ?: 0
        }
    }

    fun clearAll() {
        liveBuffer.clear()
        fiveMinBuckets.clear()
        hourlyBuckets.clear()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
            remove(KEY_5MIN)
            remove(KEY_1H)
        }
        Log.i(TAG, "All vitals data cleared")
    }

    // ── Persistence ───────────────────────────────────────────────────────

    fun saveToPrefs() {
        val s5min = fiveMinBuckets.values.joinToString("|") { it.serialize() }
        val s1h   = hourlyBuckets.values.joinToString("|") { it.serialize() }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
            putString(KEY_5MIN, s5min)
            putString(KEY_1H,   s1h)
        }
    }

    private fun loadFromPrefs() {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now   = System.currentTimeMillis()

        prefs.getString(KEY_5MIN, null)?.split("|")?.forEach { entry ->
            Bucket.deserialize(entry)?.let { b ->
                // Only restore buckets within the last hour
                if (now - b.startMs <= BUCKETS_1H * BUCKET_5MIN_MS) {
                    fiveMinBuckets[b.startMs] = b
                }
            }
        }

        prefs.getString(KEY_1H, null)?.split("|")?.forEach { entry ->
            Bucket.deserialize(entry)?.let { b ->
                // Only restore buckets within the last 24 h
                if (now - b.startMs <= BUCKETS_24H * BUCKET_1H_MS) {
                    hourlyBuckets[b.startMs] = b
                }
            }
        }
        Log.d(TAG, "Loaded ${fiveMinBuckets.size} 5-min buckets, ${hourlyBuckets.size} hourly buckets")
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private fun trimBuckets(map: LinkedHashMap<Long, Bucket>, maxSize: Int) {
        while (map.size > maxSize) map.remove(map.keys.first())
    }
}

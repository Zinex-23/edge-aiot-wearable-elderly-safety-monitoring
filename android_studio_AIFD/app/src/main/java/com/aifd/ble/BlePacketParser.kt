package com.aifd.ble

/**
 * Pure CSV packet parsers for the AIFD BLE protocol.
 *
 * Each function returns `null` on malformed input — no exceptions are thrown, so the
 * notification callback in [BleManager] can stay simple and the parsers are unit-testable
 * without any Android dependencies.
 *
 * Packet formats (see S3_BLE_test_2/BLE_PROTOCOL.md):
 *   ALERT,<seq>,<ts_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
 *   SAFE,<seq>,<ts_sec>
 *   BATCH,<seq>,<hr0|...|hr4>,<spo2_0|...|spo2_4>,<ts0|...|ts4>
 *   BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>
 */
object BlePacketParser {

    /** Top-level prefix of any well-formed packet. */
    enum class PacketKind { ALERT, SAFE, BATCH, BMI, UNKNOWN }

    fun classify(payload: String): PacketKind = when (payload.substringBefore(',', "")) {
        "ALERT" -> PacketKind.ALERT
        "SAFE"  -> PacketKind.SAFE
        "BATCH" -> PacketKind.BATCH
        "BMI"   -> PacketKind.BMI
        else    -> PacketKind.UNKNOWN
    }

    fun parseAlert(payload: String): BleManager.FallStatus? {
        val parts = payload.split(",")
        if (parts.size != 7 || parts[0] != "ALERT") return null
        return runCatching {
            BleManager.FallStatus(
                sequence     = parts[1].trim().toInt(),
                timestampSec = parts[2].trim().toLong(),
                prediction   = parts[3].trim(),
                statusCode   = parts[4].trim().toInt(),
                fallProb     = parts[5].trim().toFloat(),
                nonFallProb  = parts[6].trim().toFloat()
            )
        }.getOrNull()
    }

    /** SAFE,<seq>,<ts_sec> — returns Pair(sequence, timestampSec) or null. */
    fun parseSafe(payload: String): Pair<Int, Long>? {
        val parts = payload.split(",")
        if (parts.size != 3 || parts[0] != "SAFE") return null
        return runCatching { parts[1].trim().toInt() to parts[2].trim().toLong() }.getOrNull()
    }

    fun parseBatch(payload: String): BleManager.VitalsBatch? {
        val parts = payload.split(",")
        if (parts.size != 5 || parts[0] != "BATCH") return null
        return runCatching {
            // 255 = sensor not ready → -1 (callers filter)
            val hrs = parts[2].split("|").map {
                val v = it.trim()
                if (v == "255") -1 else v.toInt()
            }
            val sp = parts[3].split("|").map {
                val v = it.trim()
                if (v == "255") -1 else v.toInt()
            }
            val ts = parts[4].split("|").map { it.trim().toLong() }
            if (hrs.size != 5 || sp.size != 5 || ts.size != 5) return@runCatching null
            BleManager.VitalsBatch(
                sequence   = parts[1].trim().toInt(),
                heartRates = hrs,
                spo2s      = sp,
                timestamps = ts
            )
        }.getOrNull()
    }

    fun parseBmi(payload: String): BleManager.BmiSnapshot? {
        val parts = payload.split(",")
        if (parts.size != 6 || parts[0] != "BMI") return null
        return runCatching {
            BleManager.BmiSnapshot(
                sequence     = parts[1].trim().toInt(),
                timestampSec = parts[2].trim().toLong(),
                peakAccG     = parts[3].trim().toFloat(),
                peakGyroDps  = parts[4].trim().toFloat(),
                active       = parts[5].trim() == "1"
            )
        }.getOrNull()
    }
}

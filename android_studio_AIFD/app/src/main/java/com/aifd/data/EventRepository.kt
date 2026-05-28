package com.aifd.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.core.content.edit
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Date

/**
 * Singleton repository lưu trữ tất cả FallEvent dưới dạng JSON trong SharedPreferences.
 * Tồn tại qua các lần restart app (tối đa MAX_EVENTS sự kiện gần nhất).
 *
 * Cách dùng:
 *   EventRepository.init(application)   // gọi 1 lần trong ViewModel.init
 *   EventRepository.addEvent(event)
 *   EventRepository.events.collect { ... }
 */
object EventRepository {

    private const val TAG         = "EventRepository"
    private const val PREFS_NAME  = "aifd_events_v2"
    private const val KEY_EVENTS  = "events"
    private const val MAX_EVENTS  = 200

    private const val KEY_LAST_CLEARED = "last_cleared_ms"

    private var prefs: SharedPreferences? = null
    private val gson = Gson()

    private val _events = MutableStateFlow<List<FallEvent>>(emptyList())
    val events: StateFlow<List<FallEvent>> = _events.asStateFlow()

    private var _lastClearedMs: Long = 0
    val lastClearedMs: Long get() = _lastClearedMs

    fun init(context: Context) {
        if (prefs != null) return
        prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        _lastClearedMs = prefs?.getLong(KEY_LAST_CLEARED, 0L) ?: 0L
        _events.value = load()
        Log.d(TAG, "Loaded ${_events.value.size} events from storage")
    }

    fun addEvent(event: FallEvent) {
        if (event.timestamp.time <= _lastClearedMs) {
            return // Bỏ qua nếu thông báo cũ hơn thời điểm đã xóa
        }
        val updated = (listOf(event) + _events.value)
            .distinctBy { it.id }
            .sortedByDescending { it.timestamp }
            .take(MAX_EVENTS)
        _events.value = updated
        save(updated)
        Log.d(TAG, "addEvent [${event.type}] '${event.title}' total=${updated.size}")
    }

    fun updateEvent(event: FallEvent) {
        val updated = _events.value.map { if (it.id == event.id) event else it }
            .sortedByDescending { it.timestamp }
        _events.value = updated
        save(updated)
        Log.d(TAG, "updateEvent [${event.type}] '${event.title}'")
    }

    fun clearAll() {
        _lastClearedMs = System.currentTimeMillis()
        _events.value = emptyList()
        prefs?.edit {
            remove(KEY_EVENTS)
            putLong(KEY_LAST_CLEARED, _lastClearedMs)
        }
        Log.d(TAG, "All events cleared. lastClearedMs=$_lastClearedMs")
    }

    // ── Serialization ──────────────────────────────────────────────────────────

    private data class Dto(
        val id: String,
        val tsMs: Long,
        val type: String,
        val title: String,
        val status: String,
        val location: String? = null,
        val deviceName: String,
        val userResponse: String? = null,
        val detail: String? = null
    )

    private fun FallEvent.toDto() = Dto(
        id = id, tsMs = timestamp.time,
        type = type.name, title = title, status = status.name,
        location = location, deviceName = deviceName,
        userResponse = userResponse, detail = detail
    )

    private fun Dto.toEvent() = FallEvent(
        id = id, timestamp = Date(tsMs),
        type = try { EventType.valueOf(type) } catch (_: Exception) { EventType.ALERT },
        title = title,
        status = try { EventStatus.valueOf(status) } catch (_: Exception) { EventStatus.RESOLVED },
        location = location, deviceName = deviceName,
        userResponse = userResponse, detail = detail
    )

    private fun load(): List<FallEvent> {
        return try {
            val json = prefs?.getString(KEY_EVENTS, null) ?: return emptyList()
            val type = object : TypeToken<List<Dto>>() {}.type
            val dtos: List<Dto> = gson.fromJson(json, type) ?: emptyList()
            dtos.map { it.toEvent() }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load events: ${e.message}")
            emptyList()
        }
    }

    private fun save(events: List<FallEvent>) {
        try {
            prefs?.edit { putString(KEY_EVENTS, gson.toJson(events.map { it.toDto() })) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save events: ${e.message}")
        }
    }
}

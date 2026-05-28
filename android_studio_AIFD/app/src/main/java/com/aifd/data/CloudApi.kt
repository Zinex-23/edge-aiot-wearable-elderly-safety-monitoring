package com.aifd.data

import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.reflect.TypeToken
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit

// ── CONFIG ────────────────────────────────────────────────────────────────────
// Localhost testing: dùng IP máy tính trên cùng WiFi với Android.
// Khi deploy Render, đổi thành "https://ten-app.onrender.com"
private const val RENDER_URL = "https://edge-aiot-wearable-elderly-safety-4c1i.onrender.com/"

// ── DATA MODELS ───────────────────────────────────────────────────────────────

data class CloudVital(
    val id: String = "",
    val deviceId: String = "",
    val userId: String = "",
    val timestamp: String = "",
    val heartRate: Int? = null,
    val spo2: Int? = null,
    val temperature: Double? = null,
    val bloodPressure: BloodPressure? = null,
    val source: String = "ble_edge"
)

data class BloodPressure(
    val systolic: Int? = null,
    val diastolic: Int? = null
)

data class CloudFallEvent(
    val id: String = "",
    val deviceId: String = "",
    val userId: String = "",
    val timestamp: String = "",
    val type: String = "fall_auto",
    val fallProb: Double? = null,
    val resolved: Boolean = false
)

data class AuthResult(
    val ok: Boolean,
    val userId: String = "",
    val caregiverName: String = "",
    val wearerName: String = "",
    val wearerBornYear: String = "",
    val wearerGender: String = "",
    val caregiverPhone: String = "",
    val error: String = ""
)

data class CloudResult(val ok: Boolean, val error: String = "")

// ── CLIENT ────────────────────────────────────────────────────────────────────

object CloudApi {

    private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    private val gson = Gson()

    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    private fun nowIso(): String =
        DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'")
            .withZone(ZoneOffset.UTC)
            .format(Instant.now())

    // ── Auth ─────────────────────────────────────────────────────────────────

    fun register(
        username: String,
        password: String,
        profile: UserProfile
    ): AuthResult {
        val body = JsonObject().apply {
            addProperty("username",       username)
            addProperty("password",       password)
            addProperty("caregiverName",  profile.caregiverName)
            addProperty("wearerName",     profile.wearerName)
            addProperty("wearerBornYear", profile.wearerBornYear)
            addProperty("wearerGender",   profile.wearerGender)
            addProperty("caregiverPhone", profile.caregiverPhone)
        }
        return try {
            val resp = post("$RENDER_URL/api/auth/register", body.toString())
            gson.fromJson(resp, AuthResult::class.java)
        } catch (e: Exception) {
            AuthResult(ok = false, error = e.message ?: "network error")
        }
    }

    fun getProfile(username: String): AuthResult {
        return try {
            val resp = get("$RENDER_URL/api/auth/profile?username=$username")
            gson.fromJson(resp, AuthResult::class.java)
        } catch (e: Exception) {
            AuthResult(ok = false, error = e.message ?: "network error")
        }
    }

    fun updateProfile(profile: UserProfile): CloudResult {
        val body = JsonObject().apply {
            addProperty("username",       profile.username)
            addProperty("caregiverName",  profile.caregiverName)
            addProperty("wearerName",     profile.wearerName)
            addProperty("wearerBornYear", profile.wearerBornYear)
            addProperty("wearerGender",   profile.wearerGender)
            addProperty("caregiverPhone", profile.caregiverPhone)
        }
        return try {
            val resp = put("$RENDER_URL/api/auth/profile", body.toString())
            gson.fromJson(resp, CloudResult::class.java)
        } catch (e: Exception) {
            CloudResult(ok = false, error = e.message ?: "network error")
        }
    }

    fun changePassword(username: String, currentPassword: String, newPassword: String): CloudResult {
        val body = JsonObject().apply {
            addProperty("username",         username)
            addProperty("currentPassword",  currentPassword)
            addProperty("newPassword",      newPassword)
        }
        return try {
            val resp = post("$RENDER_URL/api/auth/change-password", body.toString())
            gson.fromJson(resp, CloudResult::class.java)
        } catch (e: Exception) {
            CloudResult(ok = false, error = e.message ?: "network error")
        }
    }

    fun login(username: String, password: String): AuthResult {
        val body = JsonObject().apply {
            addProperty("username", username)
            addProperty("password", password)
        }
        return try {
            val resp = post("$RENDER_URL/api/auth/login", body.toString())
            gson.fromJson(resp, AuthResult::class.java)
        } catch (e: Exception) {
            AuthResult(ok = false, error = e.message ?: "network error")
        }
    }

    // ── Vitals ────────────────────────────────────────────────────────────────

    fun postVital(
        deviceId: String,
        userId: String,
        heartRate: Int?,
        spo2: Int?,
        timestampIso: String = nowIso()
    ): CloudResult {
        val body = JsonObject().apply {
            addProperty("deviceId",    deviceId)
            addProperty("userId",      userId)
            addProperty("timestamp",   timestampIso)
            if (heartRate != null) addProperty("heartRate", heartRate) else add("heartRate", com.google.gson.JsonNull.INSTANCE)
            if (spo2      != null) addProperty("spo2",      spo2)      else add("spo2",      com.google.gson.JsonNull.INSTANCE)
            add("temperature",  com.google.gson.JsonNull.INSTANCE)
            add("bloodPressure", gson.toJsonTree(BloodPressure()))
            addProperty("source", "ble_edge")
        }
        return try {
            val resp = post("$RENDER_URL/api/vitals", body.toString())
            gson.fromJson(resp, CloudResult::class.java)
        } catch (e: Exception) {
            CloudResult(ok = false, error = e.message ?: "network error")
        }
    }

    fun getVitals(
        userId: String,
        deviceId: String,
        range: String     // "1h" or "24h"
    ): List<CloudVital> {
        return try {
            val url = "$RENDER_URL/api/vitals?userId=${userId}&deviceId=${deviceId}&range=${range}&limit=300"
            val resp = get(url)
            val obj = gson.fromJson(resp, JsonObject::class.java)
            if (!obj.get("ok").asBoolean) return emptyList()
            val type = object : TypeToken<List<CloudVital>>() {}.type
            gson.fromJson(obj.get("items"), type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    // ── Fall Events ───────────────────────────────────────────────────────────

    fun postFallEvent(
        deviceId: String,
        userId: String,
        type: String = "fall_auto",
        fallProb: Double? = null,
        timestampIso: String = nowIso()
    ): CloudResult {
        val body = JsonObject().apply {
            addProperty("deviceId",  deviceId)
            addProperty("userId",    userId)
            addProperty("timestamp", timestampIso)
            addProperty("type",      type)
            if (fallProb != null) addProperty("fallProb", fallProb)
            else add("fallProb", com.google.gson.JsonNull.INSTANCE)
        }
        return try {
            val resp = post("$RENDER_URL/api/fall_event", body.toString())
            gson.fromJson(resp, CloudResult::class.java)
        } catch (e: Exception) {
            CloudResult(ok = false, error = e.message ?: "network error")
        }
    }

    // ── Health Check ──────────────────────────────────────────────────────────

    fun isServerReachable(): Boolean {
        return try {
            val resp = get("$RENDER_URL/api/health")
            val obj = gson.fromJson(resp, JsonObject::class.java)
            obj.get("ok")?.asBoolean == true
        } catch (e: Exception) {
            false
        }
    }

    // ── HTTP primitives ───────────────────────────────────────────────────────

    private fun post(url: String, jsonBody: String): String {
        val request = Request.Builder()
            .url(url)
            .post(jsonBody.toRequestBody(JSON_MEDIA))
            .build()
        http.newCall(request).execute().use { resp ->
            return resp.body?.string() ?: throw Exception("empty response")
        }
    }

    private fun get(url: String): String {
        val request = Request.Builder().url(url).get().build()
        http.newCall(request).execute().use { resp ->
            return resp.body?.string() ?: throw Exception("empty response")
        }
    }

    private fun put(url: String, jsonBody: String): String {
        val request = Request.Builder()
            .url(url)
            .put(jsonBody.toRequestBody(JSON_MEDIA))
            .build()
        http.newCall(request).execute().use { resp ->
            return resp.body?.string() ?: throw Exception("empty response")
        }
    }
}

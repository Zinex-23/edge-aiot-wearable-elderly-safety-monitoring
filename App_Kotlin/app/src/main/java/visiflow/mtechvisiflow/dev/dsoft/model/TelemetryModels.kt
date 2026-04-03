package visiflow.mtechvisiflow.dev.dsoft.model

import com.google.gson.annotations.SerializedName

/**
 * Represents a single telemetry data point from ThingsBoard.
 * Example: { "ts": 123456789, "value": "80" }
 */
data class TelemetryEntry(
    @SerializedName("ts") val ts: Long,
    @SerializedName("value") val value: String
)

/**
 * The full telemetry response from ThingsBoard.
 * Example: { "hr": [...], "spo2": [...] }
 */
data class TelemetryResponse(
    @SerializedName("hr") val hr: List<TelemetryEntry>?,
    @SerializedName("spo2") val spo2: List<TelemetryEntry>?
)

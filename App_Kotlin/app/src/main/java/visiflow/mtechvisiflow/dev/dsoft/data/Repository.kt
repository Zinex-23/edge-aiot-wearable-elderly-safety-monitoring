package visiflow.mtechvisiflow.dev.dsoft.data

import android.util.Log
import visiflow.mtechvisiflow.dev.dsoft.model.LoginRequest
import visiflow.mtechvisiflow.dev.dsoft.model.TelemetryResponse

class Repository(private val api: ApiService = RetrofitClient.apiService) {

    companion object {
        private const val TAG = "Repository"
        private const val USERNAME = "visiflow.mtechvisiflow.dev.dsoft@gmail.com"
        private const val PASSWORD = "Dsoft@1234"
        private const val DEVICE_ID = "aa07d3e0-2a86-11f1-9abe-a93432852e45"
        private const val KEYS = "hr,spo2"
        private const val INTERVAL = 60000L
        private const val LIMIT = 1000
    }

    /** In-memory JWT token storage */
    private var jwtToken: String? = null

    /**
     * Logs in to ThingsBoard and stores the JWT in memory.
     * Returns true on success, false on failure.
     */
    suspend fun login(): Boolean {
        return try {
            Log.d(TAG, "Attempting login for user: $USERNAME")
            val response = api.login(LoginRequest(USERNAME, PASSWORD))
            if (response.isSuccessful) {
                val token = response.body()?.token
                if (!token.isNullOrEmpty()) {
                    jwtToken = token
                    Log.d("API", "Login successful, token stored.")
                    true
                } else {
                    Log.e("ERROR", "Login response body is null or token is empty.")
                    false
                }
            } else {
                Log.e("ERROR", "Login failed with HTTP ${response.code()}: ${response.errorBody()?.string()}")
                false
            }
        } catch (e: Exception) {
            Log.e("ERROR", "Login exception: ${e.message}", e)
            false
        }
    }

    /**
     * Fetches telemetry data for the configured device and time range.
     * Automatically attempts login if token is missing.
     * Returns [TelemetryResponse] on success, null on any failure.
     */
    suspend fun fetchTelemetry(startTs: Long, endTs: Long): TelemetryResponse? {
        // Ensure we have a token
        if (jwtToken == null) {
            Log.d(TAG, "No token found, attempting login before fetching telemetry.")
            val loggedIn = login()
            if (!loggedIn) {
                Log.e("ERROR", "Cannot fetch telemetry: login failed.")
                return null
            }
        }

        val token = jwtToken ?: run {
            Log.e("ERROR", "Token still null after login attempt.")
            return null
        }

        return try {
            Log.d("API", "Fetching telemetry: startTs=$startTs endTs=$endTs")
            val response = api.getTelemetry(
                authHeader = "Bearer $token",
                deviceId = DEVICE_ID,
                keys = KEYS,
                startTs = startTs,
                endTs = endTs,
                interval = INTERVAL,
                limit = LIMIT
            )
            if (response.isSuccessful) {
                val body = response.body()
                Log.d("API", "Telemetry fetched: hr=${body?.hr?.size ?: 0} entries, spo2=${body?.spo2?.size ?: 0} entries")
                body
            } else {
                Log.e("ERROR", "Telemetry fetch failed with HTTP ${response.code()}: ${response.errorBody()?.string()}")
                // If 401, clear token so next call re-authenticates
                if (response.code() == 401) {
                    jwtToken = null
                }
                null
            }
        } catch (e: Exception) {
            Log.e("ERROR", "Telemetry fetch exception: ${e.message}", e)
            null
        }
    }
}

package visiflow.mtechvisiflow.dev.dsoft.data

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import visiflow.mtechvisiflow.dev.dsoft.model.LoginRequest
import visiflow.mtechvisiflow.dev.dsoft.model.LoginResponse
import visiflow.mtechvisiflow.dev.dsoft.model.TelemetryResponse

interface ApiService {

    /**
     * Authenticate and receive a JWT token.
     */
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    /**
     * Fetch timeseries telemetry data for a specific device.
     */
    @GET("api/plugins/telemetry/DEVICE/{deviceId}/values/timeseries")
    suspend fun getTelemetry(
        @Header("Authorization") authHeader: String,
        @Path("deviceId") deviceId: String,
        @Query("keys") keys: String,
        @Query("startTs") startTs: Long,
        @Query("endTs") endTs: Long,
        @Query("interval") interval: Long = 60000L,
        @Query("limit") limit: Int = 1000
    ): Response<TelemetryResponse>
}

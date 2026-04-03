package visiflow.mtechvisiflow.dev.dsoft.viewmodel

import android.util.Log
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.github.mikephil.charting.data.Entry
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import visiflow.mtechvisiflow.dev.dsoft.data.Repository
import visiflow.mtechvisiflow.dev.dsoft.model.TelemetryEntry

/** Sealed class to represent all possible UI states. */
sealed class UiState {
    object Idle : UiState()
    object Loading : UiState()
    data class Success(
        val hrEntries: List<Entry>,
        val spo2Entries: List<Entry>
    ) : UiState()
    data class Error(val message: String) : UiState()
}

/** Time range options in milliseconds. */
enum class TimeRange(val millis: Long, val label: String) {
    ONE_HOUR(3_600_000L, "1H"),
    SIX_HOURS(21_600_000L, "6H"),
    TWENTY_FOUR_HOURS(86_400_000L, "24H")
}

class MainViewModel(
    private val repository: Repository = Repository()
) : ViewModel() {

    companion object {
        private const val TAG = "MainViewModel"
    }

    private val _uiState = MutableLiveData<UiState>(UiState.Idle)
    val uiState: LiveData<UiState> get() = _uiState

    private var currentRange: TimeRange = TimeRange.ONE_HOUR

    /** Called when a time range button is clicked. */
    fun onTimeRangeSelected(range: TimeRange) {
        currentRange = range
        loadTelemetry()
    }

    /** Initiates login and then loads telemetry data. */
    fun loadTelemetry() {
        _uiState.value = UiState.Loading

        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                val endTs = System.currentTimeMillis()
                val startTs = endTs - currentRange.millis
                Log.d(TAG, "Loading telemetry for range=${currentRange.label} startTs=$startTs endTs=$endTs")
                repository.fetchTelemetry(startTs, endTs)
            }

            if (result == null) {
                _uiState.value = UiState.Error("Failed to load data. Check logs for details.")
                return@launch
            }

            val hrEntries = parseTelemetryToEntries(result.hr)
            val spo2Entries = parseTelemetryToEntries(result.spo2)

            Log.d(TAG, "Parsed ${hrEntries.size} HR entries and ${spo2Entries.size} SpO2 entries.")

            _uiState.value = UiState.Success(hrEntries, spo2Entries)
        }
    }

    /**
     * Converts a list of [TelemetryEntry] to MPAndroidChart [Entry] list.
     * - Safely parses value using toFloatOrNull() ?: 0f
     * - Sorts by timestamp ascending
     * - X axis value is the timestamp in milliseconds (float)
     */
    private fun parseTelemetryToEntries(entries: List<TelemetryEntry>?): List<Entry> {
        if (entries.isNullOrEmpty()) {
            Log.d(TAG, "parseTelemetryToEntries: received null or empty list, returning empty.")
            return emptyList()
        }

        return entries
            .sortedBy { it.ts }
            .mapIndexed { index, entry ->
                val yValue = entry.value.toFloatOrNull() ?: run {
                    Log.e("ERROR", "Invalid value '${entry.value}' at index $index, defaulting to 0f")
                    0f
                }
                Entry(entry.ts.toFloat(), yValue)
            }
    }
}

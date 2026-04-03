package visiflow.mtechvisiflow.dev.dsoft.ui

import android.graphics.Color
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.github.mikephil.charting.formatter.ValueFormatter
import visiflow.mtechvisiflow.dev.dsoft.databinding.ActivityMainBinding
import visiflow.mtechvisiflow.dev.dsoft.viewmodel.MainViewModel
import visiflow.mtechvisiflow.dev.dsoft.viewmodel.TimeRange
import visiflow.mtechvisiflow.dev.dsoft.viewmodel.UiState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
    }

    private lateinit var binding: ActivityMainBinding
    private val viewModel: MainViewModel by viewModels()

    /** Formatter to convert X-axis timestamp (ms) to HH:mm */
    private val timeFormatter = SimpleDateFormat("HH:mm", Locale.getDefault())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupChart()
        setupButtons()
        observeViewModel()

        // Load 1H data on startup
        viewModel.onTimeRangeSelected(TimeRange.ONE_HOUR)
    }

    // ─────────────────────────────────────────────
    // Chart Setup
    // ─────────────────────────────────────────────

    private fun setupChart() {
        val chart: LineChart = binding.lineChart
        chart.apply {
            description.isEnabled = false
            setTouchEnabled(true)
            isDragEnabled = true
            setScaleEnabled(true)
            setPinchZoom(true)
            setDrawGridBackground(false)
            legend.isEnabled = true
            setNoDataText("No data available")
        }

        chart.xAxis.apply {
            position = XAxis.XAxisPosition.BOTTOM
            granularity = 1f
            setDrawGridLines(false)
            labelRotationAngle = -45f
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String {
                    return try {
                        timeFormatter.format(Date(value.toLong()))
                    } catch (e: Exception) {
                        ""
                    }
                }
            }
        }

        chart.axisLeft.apply {
            setDrawGridLines(true)
            axisMinimum = 0f
        }

        chart.axisRight.isEnabled = false

        Log.d(TAG, "Chart configured successfully.")
    }

    // ─────────────────────────────────────────────
    // Buttons
    // ─────────────────────────────────────────────

    private fun setupButtons() {
        binding.btn1h.setOnClickListener {
            Log.d(TAG, "1H button clicked")
            highlightButton(TimeRange.ONE_HOUR)
            viewModel.onTimeRangeSelected(TimeRange.ONE_HOUR)
        }
        binding.btn6h.setOnClickListener {
            Log.d(TAG, "6H button clicked")
            highlightButton(TimeRange.SIX_HOURS)
            viewModel.onTimeRangeSelected(TimeRange.SIX_HOURS)
        }
        binding.btn24h.setOnClickListener {
            Log.d(TAG, "24H button clicked")
            highlightButton(TimeRange.TWENTY_FOUR_HOURS)
            viewModel.onTimeRangeSelected(TimeRange.TWENTY_FOUR_HOURS)
        }

        // Default highlight
        highlightButton(TimeRange.ONE_HOUR)
    }

    private fun highlightButton(selected: TimeRange) {
        val activeColor = resources.getColor(android.R.color.holo_blue_dark, theme)
        val inactiveColor = resources.getColor(android.R.color.darker_gray, theme)

        binding.btn1h.setBackgroundColor(if (selected == TimeRange.ONE_HOUR) activeColor else inactiveColor)
        binding.btn6h.setBackgroundColor(if (selected == TimeRange.SIX_HOURS) activeColor else inactiveColor)
        binding.btn24h.setBackgroundColor(if (selected == TimeRange.TWENTY_FOUR_HOURS) activeColor else inactiveColor)
    }

    // ─────────────────────────────────────────────
    // Observe ViewModel
    // ─────────────────────────────────────────────

    private fun observeViewModel() {
        viewModel.uiState.observe(this) { state ->
            when (state) {
                is UiState.Idle -> {
                    binding.progressBar.visibility = View.GONE
                }
                is UiState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.lineChart.visibility = View.GONE
                    Log.d(TAG, "UI state: Loading")
                }
                is UiState.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.lineChart.visibility = View.VISIBLE
                    Log.d(TAG, "UI state: Success — rendering chart")
                    renderChart(state)
                }
                is UiState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.lineChart.visibility = View.VISIBLE
                    Log.e("ERROR", "UI state: Error — ${state.message}")
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                    // Show empty chart gracefully
                    binding.lineChart.clear()
                    binding.lineChart.setNoDataText("No data available")
                    binding.lineChart.invalidate()
                }
            }
        }
    }

    // ─────────────────────────────────────────────
    // Render Chart
    // ─────────────────────────────────────────────

    private fun renderChart(state: UiState.Success) {
        val dataSets = mutableListOf<LineDataSet>()

        if (state.hrEntries.isNotEmpty()) {
            val hrDataSet = LineDataSet(state.hrEntries, "HR (bpm)").apply {
                color = Color.RED
                setCircleColor(Color.RED)
                lineWidth = 2f
                circleRadius = 2f
                setDrawCircleHole(false)
                setDrawValues(false)
                mode = LineDataSet.Mode.CUBIC_BEZIER
                cubicIntensity = 0.2f
            }
            dataSets.add(hrDataSet)
            Log.d(TAG, "HR dataset added with ${state.hrEntries.size} entries.")
        } else {
            Log.d(TAG, "HR entries empty — not adding dataset.")
        }

        if (state.spo2Entries.isNotEmpty()) {
            val spo2DataSet = LineDataSet(state.spo2Entries, "SpO2 (%)").apply {
                color = Color.BLUE
                setCircleColor(Color.BLUE)
                lineWidth = 2f
                circleRadius = 2f
                setDrawCircleHole(false)
                setDrawValues(false)
                mode = LineDataSet.Mode.CUBIC_BEZIER
                cubicIntensity = 0.2f
            }
            dataSets.add(spo2DataSet)
            Log.d(TAG, "SpO2 dataset added with ${state.spo2Entries.size} entries.")
        } else {
            Log.d(TAG, "SpO2 entries empty — not adding dataset.")
        }

        if (dataSets.isEmpty()) {
            binding.lineChart.clear()
            binding.lineChart.setNoDataText("No data for selected period")
            binding.lineChart.invalidate()
            Log.d(TAG, "No data to render in chart.")
            return
        }

        val lineData = LineData(dataSets.map { it })
        binding.lineChart.data = lineData
        binding.lineChart.animateX(500)
        binding.lineChart.invalidate()
        Log.d(TAG, "Chart updated with ${dataSets.size} datasets.")
    }
}

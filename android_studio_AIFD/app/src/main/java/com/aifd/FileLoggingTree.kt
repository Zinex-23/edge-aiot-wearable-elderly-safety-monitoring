package com.aifd

import android.util.Log
import timber.log.Timber
import java.io.BufferedWriter
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class FileLoggingTree(externalFilesDir: File) : Timber.Tree() {

    private val timeFormatter = SimpleDateFormat("HH:mm:ss.SSS", Locale.US)
    private val logFile: File
    private val writer: BufferedWriter

    init {
        val logsDir = File(externalFilesDir, "logs")
        logsDir.mkdirs()
        val stamp = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US).format(Date())
        logFile = File(logsDir, "log_$stamp.txt")
        writer = BufferedWriter(FileWriter(logFile, true))
    }

    override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
        val level = when (priority) {
            Log.VERBOSE -> "V"
            Log.DEBUG   -> "D"
            Log.INFO    -> "I"
            Log.WARN    -> "W"
            Log.ERROR   -> "E"
            Log.ASSERT  -> "A"
            else        -> "?"
        }
        val time = timeFormatter.format(Date())
        writer.write("$time $level/$tag: $message")
        writer.newLine()
        if (t != null) {
            writer.write(Log.getStackTraceString(t))
            writer.newLine()
        }
        writer.flush()
    }

    fun getLogFilePath(): String = logFile.absolutePath

    fun close() = writer.close()
}

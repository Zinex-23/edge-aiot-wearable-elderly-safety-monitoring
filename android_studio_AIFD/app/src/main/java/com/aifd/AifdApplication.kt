package com.aifd

import android.app.Application
import timber.log.Timber

class AifdApplication : Application() {

    private var fileLoggingTree: FileLoggingTree? = null

    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            val externalDir = getExternalFilesDir(null) ?: filesDir
            fileLoggingTree = FileLoggingTree(externalDir)
            Timber.plant(Timber.DebugTree(), fileLoggingTree!!)
            Timber.i("Log file: ${fileLoggingTree!!.getLogFilePath()}")
        }
    }

    override fun onTerminate() {
        super.onTerminate()
        fileLoggingTree?.close()
    }
}

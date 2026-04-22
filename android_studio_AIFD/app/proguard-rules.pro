# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in the Android SDK tools proguard configuration.

# Keep Compose-related classes
-keep class androidx.compose.** { *; }

# Keep data classes
-keep class com.aifd.data.** { *; }

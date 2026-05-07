package com.aifd.ui.localization

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Stable
import androidx.compose.runtime.compositionLocalOf
import com.aifd.data.EventType
import com.aifd.data.UserRole
import java.util.Locale

enum class AppLanguage {
    ENGLISH,
    VIETNAMESE
}

@Stable
class AppStrings(private val currentLanguage: AppLanguage) {
    private val vi = currentLanguage == AppLanguage.VIETNAMESE
    val locale: Locale = if (vi) Locale("vi") else Locale.US

    val appName get() = "AIFD"
    val home get() = if (vi) "Trang chủ" else "Home"
    val health get() = if (vi) "Sức khỏe" else "Health"
    val alerts get() = if (vi) "Cảnh báo" else "Alerts"
    val settings get() = if (vi) "Cài đặt" else "Settings"
    val back get() = if (vi) "Quay lại" else "Back"
    val save get() = if (vi) "Lưu" else "Save"
    val cancel get() = if (vi) "Hủy" else "Cancel"
    val details get() = if (vi) "Chi tiết" else "Details"
    val location get() = if (vi) "Vị trí" else "Location"
    val time get() = if (vi) "Thời gian" else "Time"
    val device get() = if (vi) "Thiết bị" else "Device"
    val language get() = if (vi) "Ngôn ngữ" else "Language"
    val theme get() = if (vi) "Giao diện" else "Theme"
    val role get() = if (vi) "Vai trò" else "Role"
    val light get() = if (vi) "Sáng" else "Light"
    val dark get() = if (vi) "Tối" else "Dark"
    val system get() = if (vi) "Hệ thống" else "System"
    val english get() = if (vi) "Tiếng Anh" else "English"
    val vietnamese get() = if (vi) "Tiếng Việt" else "Vietnamese"
    val wearer get() = if (vi) "Người đeo" else "Wearer"
    val caregiver get() = if (vi) "Người chăm sóc" else "Caregiver"
    val chooseTheme get() = if (vi) "Chọn giao diện" else "Choose Theme"
    val chooseLanguage get() = if (vi) "Chọn ngôn ngữ" else "Choose Language"
    val chooseRole get() = if (vi) "Chọn vai trò của bạn" else "Choose your role"
    val roleIntro get() = if (vi) "Chọn cách bạn sẽ sử dụng ứng dụng này." else "Select how you will use this app."
    val continueLabel get() = if (vi) "Tiếp tục" else "Continue"
    val switchRole get() = if (vi) "Chuyển vai trò" else "Switch role"
    val appearance get() = if (vi) "Giao diện" else "Appearance"
    val connectedDevice get() = if (vi) "Thiết bị đang kết nối" else "Connected Device"
    val deviceDetails get() = if (vi) "Chi tiết thiết bị" else "Device Details"
    val alertSettings get() = if (vi) "Cài đặt cảnh báo" else "Alert Settings"
    val fallSensitivity get() = if (vi) "Độ nhạy phát hiện ngã" else "Fall Detection Sensitivity"
    val fallSensitivityHint get() = if (vi) "Điều chỉnh độ nhạy khi phát hiện ngã" else "Adjust how sensitive the fall detection is"
    val low get() = if (vi) "Thấp" else "Low"
    val medium get() = if (vi) "Trung bình" else "Medium"
    val high get() = if (vi) "Cao" else "High"
    fun sensitivityDescription(level: String) = when (level) {
        "low" -> if (vi) "Cảnh báo ít hơn, ngưỡng phát hiện cao hơn" else "Less frequent alerts, higher threshold for detection"
        "high" -> if (vi) "Nhạy hơn, có thể tăng cảnh báo nhầm" else "More sensitive detection, may increase false alerts"
        else -> if (vi) "Cân bằng cho sử dụng hằng ngày" else "Balanced detection for everyday use"
    }
    val emergencySection get() = if (vi) "Khẩn cấp" else "Emergency"
    val emergencyContacts get() = if (vi) "Liên hệ khẩn cấp" else "Emergency Contacts"
    val manageContacts get() = if (vi) "Quản lý liên hệ" else "Manage contacts"
    val notificationSettings get() = if (vi) "Cài đặt thông báo" else "Notification Settings"
    val manageAlerts get() = if (vi) "Quản lý cảnh báo" else "Manage alerts"
    val account get() = if (vi) "Tài khoản" else "Account"
    val profile get() = if (vi) "Hồ sơ" else "Profile"
    val viewProfile get() = if (vi) "Xem hồ sơ" else "View profile"
    val helpSupport get() = if (vi) "Trợ giúp và hỗ trợ" else "Help & Support"
    val logout get() = if (vi) "Đăng xuất" else "Log Out"
    val logoutTitle get() = if (vi) "Đăng xuất?" else "Log Out?"
    val logoutMessage get() = if (vi) "Bạn có chắc muốn đăng xuất? Ứng dụng sẽ quay lại màn hình đăng nhập." else "Are you sure you want to log out? The app will return to the sign in screen."
    val deviceDisconnected get() = if (vi) "Chưa kết nối thiết bị đeo" else "Wearable not connected"
    val tapToReconnect get() = if (vi) "Chạm để kết nối" else "Tap to connect"
    val connect get() = if (vi) "Kết nối" else "Connect"
    val lowBattery get() = if (vi) "Pin yếu" else "Low Battery"
    val chargeSoon get() = if (vi) "Vui lòng sạc thiết bị sớm" else "Please charge your device soon"
    val realTimeMonitoring get() = if (vi) "Đang theo dõi thời gian thực" else "Real-time monitoring active"
    val heartRate get() = if (vi) "Nhịp tim" else "Heart Rate"
    val bloodOxygen get() = if (vi) "Oxy máu (SpO2)" else "Blood Oxygen (SpO2)"
    val stepsToday get() = if (vi) "Bước chân" else "Steps"
    val emergency get() = if (vi) "Khẩn cấp" else "Emergency"
    val viewDetails get() = if (vi) "Xem chi tiết" else "View Details"
    val pairDevice get() = if (vi) "Ghép đôi thiết bị" else "Pair Device"
    val wearerOverview get() = if (vi) "Tổng quan người đeo" else "Wearer Overview"
    val caregiverHero get() = if (vi) "Bạn đang theo dõi dữ liệu thời gian thực và cảnh báo bất thường của người đeo." else "You are viewing the wearer's realtime data and abnormal alerts."
    val caregiverNoBle get() = if (vi) "Vai trò này không cần kết nối BLE trực tiếp." else "This role does not require a direct BLE connection."
    val filterAll get() = if (vi) "Tất cả" else "All"
    val filterFalls get() = if (vi) "Ngã" else "Falls"
    val filterDisconnects get() = if (vi) "Mất kết nối" else "Disconnects"
    val filterAlerts get() = if (vi) "Cảnh báo" else "Alerts"
    val noEventsFound get() = if (vi) "Không có sự kiện" else "No events found"
    val alertHistoryEmpty get() = if (vi) "Lịch sử cảnh báo sẽ hiển thị tại đây" else "Your alert history will appear here"
    fun noFilteredEvents(filter: String) = if (vi) "Không có sự kiện $filter" else "No $filter events recorded"
    val resolved get() = if (vi) "Đã xử lý" else "Resolved"
    val pending get() = if (vi) "Đang chờ" else "Pending"
    val dismissed get() = if (vi) "Đã bỏ qua" else "Dismissed"
    val justNow get() = if (vi) "Vừa xong" else "Just now"
    fun hoursAgo(hours: Long) = if (vi) "$hours giờ trước" else "${hours}h ago"
    fun daysAgo(days: Long) = if (vi) "$days ngày trước" else "${days}d ago"
    val connectDevice get() = if (vi) "Kết nối thiết bị" else "Connect Device"
    val scan get() = if (vi) "Quét" else "Scan"
    val scanningDevices get() = if (vi) "Đang quét thiết bị..." else "Scanning for devices..."
    val scanningHint get() = if (vi) "Hãy đảm bảo thiết bị đang bật và ở gần" else "Make sure your device is turned on and nearby"
    fun nearbyDevices(count: Int) = if (vi) "Thiết bị gần đây ($count)" else "Nearby Devices ($count)"
    val noDevicesFound get() = if (vi) "Không tìm thấy thiết bị" else "No devices found"
    val scanAgain get() = if (vi) "Quét lại" else "Scan Again"
    val excellent get() = if (vi) "Rất tốt" else "Excellent"
    val good get() = if (vi) "Tốt" else "Good"
    val fair get() = if (vi) "Trung bình" else "Fair"
    val weak get() = if (vi) "Yếu" else "Weak"
    val connected get() = if (vi) "Đã kết nối" else "Connected"
    val disconnected get() = if (vi) "Đã ngắt kết nối" else "Disconnected"
    val connecting get() = if (vi) "Đang kết nối..." else "Connecting..."
    val discoveringDevice get() = if (vi) "Đang tìm thiết bị..." else "Discovering device..."
    val establishingConnection get() = if (vi) "Đang thiết lập kết nối..." else "Establishing connection..."
    val syncingData get() = if (vi) "Đang đồng bộ dữ liệu..." else "Syncing data..."
    val almostDone get() = if (vi) "Gần xong..." else "Almost done..."
    val cantFindDevice get() = if (vi) "Không tìm thấy thiết bị?" else "Can't find your device?"
    val troubleshootingGuide get() = if (vi) "Hướng dẫn xử lý sự cố" else "Troubleshooting Guide"
    val noDeviceConnected get() = if (vi) "Chưa kết nối thiết bị" else "No Device Connected"
    val connectDeviceToView get() = if (vi) "Hãy kết nối thiết bị để xem chi tiết" else "Connect a device to view its details"
    val deviceId get() = if (vi) "Mã thiết bị" else "Device ID"
    val battery get() = if (vi) "Pin" else "Battery"
    val signalStrength get() = if (vi) "Cường độ tín hiệu" else "Signal Strength"
    val lastSync get() = if (vi) "Đồng bộ gần nhất" else "Last Sync"
    val firmwareVersion get() = if (vi) "Phiên bản firmware" else "Firmware Version"
    val reconnect get() = if (vi) "Kết nối lại" else "Reconnect"
    val disconnect get() = if (vi) "Ngắt kết nối" else "Disconnect"
    val renameDevice get() = if (vi) "Đổi tên thiết bị" else "Rename Device"
    val disconnectDeviceTitle get() = if (vi) "Ngắt kết nối thiết bị?" else "Disconnect Device?"
    fun disconnectDeviceMessage(name: String) = if (vi) "Bạn có chắc muốn ngắt kết nối $name? Bạn sẽ dừng nhận dữ liệu sức khỏe và cảnh báo ngã." else "Are you sure you want to disconnect $name? You will stop receiving health data and fall alerts."
    val live get() = "Live"
    val oneHour get() = if (vi) "1 giờ" else "1 Hour"
    val twentyFourHours get() = if (vi) "24 giờ" else "24 Hours"
    val average get() = if (vi) "Trung bình" else "Average"
    val min get() = "Min"
    val max get() = "Max"
    val current get() = if (vi) "Hiện tại" else "Current"
    val heartRateTrend get() = if (vi) "Xu hướng nhịp tim" else "Heart Rate Trend"
    val spo2Trend get() = if (vi) "Xu hướng SpO2" else "SpO2 Trend"
    val updating get() = if (vi) "Đang cập nhật" else "Updating"
    val now get() = if (vi) "Bây giờ" else "Now"
    val normal get() = if (vi) "Bình thường" else "Normal"
    val unknown get() = if (vi) "Không rõ" else "Unknown"
    val normalSpo2Range get() = if (vi) "Mức SpO2 bình thường: 95-100%" else "Normal SpO2 range: 95-100%"
    val lowSpo2Warning get() = if (vi) "Nếu chỉ số xuống dưới 90%, đây là dấu hiệu nguy hiểm cần hỗ trợ y tế." else "A reading below 90% is a critical sign that requires medical attention."
    val normalHeartRateRange get() = if (vi) "Nhịp tim bình thường: 60-100 bpm" else "Normal heart rate: 60-100 bpm"
    val heartRateWarning get() = if (vi) "Nhịp tim lúc nghỉ ngơi thường ổn định. Nếu thấy bất thường kéo dài, hãy tham khảo ý kiến bác sĩ." else "Resting heart rate is usually stable. If you notice persistent abnormalities, consult a doctor."
    val today get() = if (vi) "Hôm nay" else "Today"
    val goal get() = if (vi) "Mục tiêu" else "Goal"
    fun dailyGoalProgress(percent: Int) = if (vi) "$percent% mục tiêu hằng ngày" else "$percent% of daily goal"
    val thisWeek get() = if (vi) "Tuần này" else "This Week"
    val weeklyAverage get() = if (vi) "Trung bình tuần" else "Weekly Average"
    val weeklyTotal get() = if (vi) "Tổng tuần" else "Weekly Total"
    val stepsPerDay get() = if (vi) "bước/ngày" else "steps/day"
    val eventNotFound get() = if (vi) "Không tìm thấy sự kiện" else "Event not found"
    val timeline get() = if (vi) "Tiến trình" else "Timeline"
    val userResponse get() = if (vi) "Phản hồi người dùng" else "User Response"
    val fallDetected get() = if (vi) "Phát hiện có va chạm mạnh!" else "Severe collision detected!"
    val alertTriggered get() = if (vi) "Đã kích hoạt cảnh báo" else "Alert Triggered"
    val eventResolved get() = if (vi) "Sự kiện đã xử lý" else "Event Resolved"
    val unusualMotionDetected get() = if (vi) "Phát hiện mẫu chuyển động bất thường" else "Unusual motion pattern detected"
    val countdownStarted get() = if (vi) "Đã bắt đầu đếm ngược 15 giây" else "15 second countdown started"
    val userOkay get() = if (vi) "Người dùng xác nhận an toàn" else "User confirmed they are okay"
    val emergencyContactsNotified get() = if (vi) "Đã thông báo liên hệ khẩn cấp" else "Emergency contacts notified"
    val noFurtherAction get() = if (vi) "Không cần thao tác thêm" else "No further action required"
    val callingForHelp get() = if (vi) "Đang gọi hỗ trợ..." else "Calling for Help..."
    val notifyingContacts get() = if (vi) "Đang thông báo đến liên hệ khẩn cấp" else "Emergency contacts are being notified"
    val okayPrompt get() = if (vi) "Hệ thống sẽ gửi tin nhắn cứu hộ sau 15 giây. Nhấn hủy nếu bạn vẫn ổn" else "Emergency contacts will be notified in 15 seconds. Dismiss if you are okay."
    fun callingContactsIn(seconds: Int) = if (vi) "Sẽ gọi liên hệ khẩn cấp sau ${seconds} giây" else "Calling emergency contacts in ${seconds}s"
    val estimatedLivingRoom get() = if (vi) "Phòng khách (ước tính)" else "Living Room (estimated)"
    fun detectedBy(deviceName: String) = if (vi) "Phát hiện bởi $deviceName" else "Detected by $deviceName"
    val imSafe get() = if (vi) "Tôi vẫn ổn (Hủy)" else "I'm Safe (Cancel)"
    val callForHelp get() = if (vi) "Gọi hỗ trợ" else "Call for Help"
    val notConnected get() = if (vi) "Chưa kết nối" else "Not connected"
    val viewInfo get() = if (vi) "Xem thông tin" else "View info"
    val roleWearerSummary get() = if (vi) "Kết nối đồng hồ thông minh qua BLE, nhận dữ liệu và nhận cảnh báo cho chính bạn." else "Connect to the wearable via BLE, receive data, and get alerts related to yourself."
    val roleCaregiverSummary get() = if (vi) "Xem dữ liệu thời gian thực của người đeo, nhận cảnh báo khẩn cấp và theo dõi lịch sử." else "View the wearer's realtime data, receive emergency alerts, and monitor history."
    val username get() = if (vi) "Tên đăng nhập" else "Username"
    val password get() = if (vi) "Mật khẩu" else "Password"
    val signIn get() = if (vi) "Đăng nhập" else "Sign In"
    val signInTitle get() = if (vi) "Đăng nhập vào AIFD" else "Sign in to AIFD"
    val signInHint get() = if (vi) "Tài khoản mặc định: dien572 / dien562003" else "Default account: dien572 / dien562003"
    val invalidCredentials get() = if (vi) "Sai tên đăng nhập hoặc mật khẩu." else "Incorrect username or password."
    val welcomeBack get() = if (vi) "Chào mừng quay lại" else "Welcome back"
    val deviceNameLabel get() = if (vi) "Thiết bị" else "Device"
    val batteryRemaining get() = if (vi) "Pin còn lại" else "Battery"
    val alertsCount get() = if (vi) "Số alarm" else "Alerts"
    val hello get() = if (vi) "Xin chào" else "Hello"
    val signUpTitle get() = if (vi) "Đăng ký tài khoản" else "Create Account"
    val signUpHint get() = if (vi) "Nhập thông tin bên dưới để bắt đầu" else "Enter your details to get started"
    val register get() = if (vi) "Đăng ký" else "Register"
    val dontHaveAccount get() = if (vi) "Chưa có tài khoản? " else "Don't have an account? "
    val caregiverNameLabel get() = if (vi) "Tên người chăm sóc" else "Caregiver Name"
    val wearerNameLabel get() = if (vi) "Tên người đeo" else "Wearer Name"
    val wearerAgeLabel get() = if (vi) "Tuổi người đeo" else "Wearer Age"
    val wearerGenderLabel get() = if (vi) "Giới tính người đeo" else "Wearer Gender"
    val caregiverPhoneLabel get() = if (vi) "Số điện thoại người chăm sóc" else "Caregiver Phone"
    val male get() = if (vi) "Nam" else "Male"
    val female get() = if (vi) "Nữ" else "Female"
    val other get() = if (vi) "Khác" else "Other"

    fun getRandomGreeting(userName: String, role: UserRole): String {
        val name = if (userName.isBlank()) {
            if (role == UserRole.WEARER) wearer else caregiver
        } else userName

        val greetingsVn = listOf(
            // Mẫu 1: thân mật, nhẹ nhàng
            "Chào $name, hôm nay mình cùng theo dõi sức khỏe nhé.",
            "Nhớ dành vài phút kiểm tra chỉ số của $name nha.",
            "Hôm nay $name uống đủ nước chưa?",
            "Nếu thấy mệt, $name nên nghỉ ngơi một chút nhé.",
            "Đi bộ thêm một chút nữa là gần đạt mục tiêu rồi đó $name.",
            "Chỉ số của $name vừa được cập nhật, mình xem qua nhé.",
            "Bạn đang làm rất tốt, nhớ giữ nhịp sinh hoạt đều đặn nha $name.",
            "Đừng quên hít thở sâu và thư giãn một lát nhé $name.",
            // Mẫu 2: gần gũi hơn, kiểu trợ lý đồng hành
            "Xin chào, mình luôn ở đây để cùng $name chăm sóc sức khỏe.",
            "Hôm nay cơ thể $name thế nào? Mình xem nhanh chỉ số nhé.",
            "Có một vài chỉ số cần $name chú ý một chút đó.",
            "Bạn nhớ nghỉ ngơi đầy đủ để cơ thể phục hồi tốt hơn nhé $name.",
            "Cố thêm chút nữa thôi, mục tiêu vận động hôm nay sắp đạt rồi $name.",
            "Nếu cảm thấy không ổn, $name nên theo dõi kỹ hơn nhé.",
            "Mình đã ghi lại dữ liệu mới nhất cho $name rồi.",
            "Chúc $name một ngày thật khỏe và nhẹ nhàng."
        )

        val greetingsEn = listOf(
            // Version 1: warm and friendly
            "Hi $name, let’s check in on your health today.",
            "Just a gentle reminder to take a quick look at your stats, $name.",
            "Have you had enough water today, $name?",
            "If you feel tired, $name, take a short break and rest a little.",
            "You are getting close to your step goal $name, keep going.",
            "Your latest health data is ready to review, $name.",
            "You are doing well today $name, keep up your healthy routine.",
            "Don’t forget to take a deep breath and relax for a moment $name.",
            // Version 2: supportive assistant tone
            "Hello $name, I’m here to help you take care of your health.",
            "How are you feeling today, $name? Let’s review your latest readings.",
            "A few health indicators may need a little attention, $name.",
            "Please remember to rest well and take care of yourself, $name.",
            "You are almost at your activity goal for today, $name.",
            "I’ve updated your latest health data for you, $name.",
            "If something feels unusual $name, keep an eye on your readings.",
            "Wishing you a healthy and calm day, $name."
        )

        val list = if (vi) greetingsVn else greetingsEn
        // Use a stable hash of the day + name to keep it consistent throughout the day
        val seed = java.util.Calendar.getInstance().get(java.util.Calendar.DAY_OF_YEAR) + name.hashCode()
        return list[kotlin.math.abs(seed) % list.size]
    }

    fun eventTitle(type: EventType) = when (type) {
        EventType.FALL -> fallDetected
        EventType.DISCONNECT -> deviceDisconnected
        EventType.LOW_BATTERY -> lowBattery
        EventType.ALERT -> emergency
    }
}

val LocalAppLanguage = compositionLocalOf { AppLanguage.ENGLISH }
val LocalAppStrings = compositionLocalOf { AppStrings(AppLanguage.ENGLISH) }

@Composable
fun ProvideAppStrings(
    language: AppLanguage,
    content: @Composable () -> Unit
) {
    CompositionLocalProvider(
        LocalAppLanguage provides language,
        LocalAppStrings provides AppStrings(language),
        content = content
    )
}

object AppLocalizations {
    val strings: AppStrings
        @Composable
        get() = LocalAppStrings.current

    val language: AppLanguage
        @Composable
        get() = LocalAppLanguage.current
}

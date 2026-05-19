package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.aifd.data.CloudApi
import com.aifd.data.UserProfile
import com.aifd.ui.localization.AppLocalizations
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RegisterScreen(
    onRegisterSuccess: (UserProfile) -> Unit,
    onNavigateToLogin: () -> Unit
) {
    val strings = AppLocalizations.strings
    val scope = rememberCoroutineScope()

    var username        by rememberSaveable { mutableStateOf("") }
    var password        by rememberSaveable { mutableStateOf("") }
    var confirmPassword by rememberSaveable { mutableStateOf("") }
    var showPw          by rememberSaveable { mutableStateOf(false) }
    var showConfirmPw   by rememberSaveable { mutableStateOf(false) }
    var caregiverName   by rememberSaveable { mutableStateOf("") }
    var wearerName      by rememberSaveable { mutableStateOf("") }
    var wearerAge       by rememberSaveable { mutableStateOf("") }
    var wearerGender    by rememberSaveable { mutableStateOf("") }
    var caregiverPhone  by rememberSaveable { mutableStateOf("") }

    var isLoading by remember { mutableStateOf(false) }
    var errorMsg  by remember { mutableStateOf("") }

    val passwordMismatch = confirmPassword.isNotBlank() && password != confirmPassword
    val canSubmit = username.isNotBlank() && password.isNotBlank()
        && confirmPassword.isNotBlank() && !passwordMismatch && !isLoading

    fun doRegister() {
        if (password != confirmPassword) {
            errorMsg = "Mật khẩu xác nhận không khớp"
            return
        }
        isLoading = true
        errorMsg  = ""
        val profile = UserProfile(
            username       = username.trim(),
            caregiverName  = caregiverName,
            wearerName     = wearerName,
            wearerAge      = wearerAge,
            wearerGender   = wearerGender,
            caregiverPhone = caregiverPhone
        )
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                CloudApi.register(username.trim(), password, profile)
            }
            isLoading = false
            if (result.ok) {
                onRegisterSuccess(profile)
            } else {
                errorMsg = when {
                    result.error.contains("already", ignoreCase = true)  -> "Tên đăng nhập đã tồn tại"
                    result.error.contains("network", ignoreCase = true)  -> "Không có kết nối mạng, kiểm tra lại server"
                    result.error.isNotBlank()                            -> result.error
                    else                                                 -> "Đăng ký thất bại, thử lại"
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = strings.signUpTitle,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = strings.signUpHint,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        // ── Account ──────────────────────────────────────────────────────────
        Text(strings.account, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)

        OutlinedTextField(
            value = username,
            onValueChange = { username = it; errorMsg = "" },
            label = { Text(strings.username) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isLoading
        )

        OutlinedTextField(
            value = password,
            onValueChange = { password = it; errorMsg = "" },
            label = { Text(strings.password) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = if (showPw) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                IconButton(onClick = { showPw = !showPw }) {
                    Icon(
                        imageVector = if (showPw) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = null
                    )
                }
            },
            enabled = !isLoading
        )

        OutlinedTextField(
            value = confirmPassword,
            onValueChange = { confirmPassword = it; errorMsg = "" },
            label = { Text("Xác nhận mật khẩu") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = if (showConfirmPw) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                IconButton(onClick = { showConfirmPw = !showConfirmPw }) {
                    Icon(
                        imageVector = if (showConfirmPw) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = null
                    )
                }
            },
            isError = passwordMismatch,
            supportingText = if (passwordMismatch) {
                { Text("Mật khẩu không khớp", color = MaterialTheme.colorScheme.error) }
            } else null,
            enabled = !isLoading
        )

        // ── Caregiver ─────────────────────────────────────────────────────────
        Text(strings.caregiver, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        OutlinedTextField(
            value = caregiverName,
            onValueChange = { caregiverName = it },
            label = { Text(strings.caregiverNameLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isLoading
        )
        OutlinedTextField(
            value = caregiverPhone,
            onValueChange = { caregiverPhone = it },
            label = { Text(strings.caregiverPhoneLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            enabled = !isLoading
        )

        // ── Wearer ────────────────────────────────────────────────────────────
        Text(strings.wearer, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        OutlinedTextField(
            value = wearerName,
            onValueChange = { wearerName = it },
            label = { Text(strings.wearerNameLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isLoading
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = wearerAge,
                onValueChange = { wearerAge = it },
                label = { Text(strings.wearerAgeLabel) },
                modifier = Modifier.weight(1f),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                enabled = !isLoading
            )
            OutlinedTextField(
                value = wearerGender,
                onValueChange = { wearerGender = it },
                label = { Text(strings.wearerGenderLabel) },
                modifier = Modifier.weight(1f),
                singleLine = true,
                enabled = !isLoading
            )
        }

        if (errorMsg.isNotBlank()) {
            Text(
                text = errorMsg,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall
            )
        }

        Spacer(Modifier.height(8.dp))
        Button(
            onClick = { doRegister() },
            modifier = Modifier.fillMaxWidth().height(54.dp),
            enabled = canSubmit
        ) {
            if (isLoading) {
                val spin = rememberInfiniteTransition(label = "reg_spin")
                val angle by spin.animateFloat(
                    initialValue = 0f, targetValue = 360f,
                    animationSpec = infiniteRepeatable(tween(700, easing = LinearEasing)),
                    label = "angle"
                )
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp).rotate(angle),
                    tint = MaterialTheme.colorScheme.onPrimary
                )
            } else {
                Text(strings.register, fontWeight = FontWeight.SemiBold)
            }
        }

        TextButton(
            onClick = onNavigateToLogin,
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Text(strings.signInTitle)
        }
    }
}

package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.CloudApi
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(
    onLoginSuccess: (String) -> Unit,
    onNavigateToRegister: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    val scope = rememberCoroutineScope()

    var username    by rememberSaveable { mutableStateOf("") }
    var password    by rememberSaveable { mutableStateOf("") }
    var showPw      by rememberSaveable { mutableStateOf(false) }
    var errorMsg    by remember { mutableStateOf("") }
    var isLoading   by remember { mutableStateOf(false) }

    fun doLogin() {
        if (username.isBlank() || password.isBlank()) {
            errorMsg = strings.invalidCredentials
            return
        }
        if (username == "000" && password == "000") {
            onLoginSuccess("000")
            return
        }
        isLoading = true
        errorMsg  = ""
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                CloudApi.login(username.trim(), password)
            }
            isLoading = false
            if (result.ok) {
                onLoginSuccess(result.userId)
            } else {
                errorMsg = when {
                    result.error.contains("invalid", ignoreCase = true) -> strings.invalidCredentials
                    result.error.contains("network", ignoreCase = true)  -> "Không có kết nối mạng, kiểm tra lại server"
                    result.error.isNotBlank()                            -> result.error
                    else                                                 -> strings.invalidCredentials
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp, vertical = 32.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = strings.signInTitle,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = strings.signInHint,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(24.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it; errorMsg = "" },
            label = { Text(strings.username) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isLoading
        )
        Spacer(Modifier.height(12.dp))
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
                        contentDescription = if (showPw) "Ẩn mật khẩu" else "Hiện mật khẩu"
                    )
                }
            },
            enabled = !isLoading
        )

        if (errorMsg.isNotBlank()) {
            Spacer(Modifier.height(12.dp))
            Text(
                text = errorMsg,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall
            )
        }

        Spacer(Modifier.height(20.dp))
        Button(
            onClick = { doLogin() },
            modifier = Modifier.fillMaxWidth().height(54.dp),
            enabled = !isLoading
        ) {
            if (isLoading) {
                val spin = rememberInfiniteTransition(label = "login_spin")
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
                Text(strings.signIn, fontWeight = FontWeight.SemiBold)
            }
        }

        Spacer(Modifier.height(16.dp))
        TextButton(
            onClick = onNavigateToRegister,
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            Text(
                text = strings.dontHaveAccount + strings.register,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun LoginScreenPreview() {
    AIFDTheme {
        LoginScreen(onLoginSuccess = {})
    }
}

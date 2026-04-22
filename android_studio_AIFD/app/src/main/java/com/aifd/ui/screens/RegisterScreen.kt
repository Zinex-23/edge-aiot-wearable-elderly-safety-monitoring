package com.aifd.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.aifd.data.UserProfile
import com.aifd.ui.localization.AppLocalizations

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RegisterScreen(
    onRegisterSuccess: (UserProfile) -> Unit,
    onNavigateToLogin: () -> Unit
) {
    val strings = AppLocalizations.strings
    var username by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var caregiverName by rememberSaveable { mutableStateOf("") }
    var wearerName by rememberSaveable { mutableStateOf("") }
    var wearerAge by rememberSaveable { mutableStateOf("") }
    var wearerGender by rememberSaveable { mutableStateOf("") }
    var caregiverPhone by rememberSaveable { mutableStateOf("") }

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

        // Account Info
        Text(strings.account, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text(strings.username) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text(strings.password) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = PasswordVisualTransformation()
        )

        // Caregiver Info
        Text(strings.caregiver, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        OutlinedTextField(
            value = caregiverName,
            onValueChange = { caregiverName = it },
            label = { Text(strings.caregiverNameLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = caregiverPhone,
            onValueChange = { caregiverPhone = it },
            label = { Text(strings.caregiverPhoneLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone)
        )

        // Wearer Info
        Text(strings.wearer, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        OutlinedTextField(
            value = wearerName,
            onValueChange = { wearerName = it },
            label = { Text(strings.wearerNameLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = wearerAge,
                onValueChange = { wearerAge = it },
                label = { Text(strings.wearerAgeLabel) },
                modifier = Modifier.weight(1f),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
            )
            OutlinedTextField(
                value = wearerGender,
                onValueChange = { wearerGender = it },
                label = { Text(strings.wearerGenderLabel) },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
        }

        Spacer(Modifier.height(8.dp))
        Button(
            onClick = {
                onRegisterSuccess(
                    UserProfile(
                        username = username,
                        caregiverName = caregiverName,
                        wearerName = wearerName,
                        wearerAge = wearerAge,
                        wearerGender = wearerGender,
                        caregiverPhone = caregiverPhone
                    )
                )
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(54.dp),
            enabled = username.isNotBlank() && password.isNotBlank()
        ) {
            Text(strings.register, fontWeight = FontWeight.SemiBold)
        }

        TextButton(
            onClick = onNavigateToLogin,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(strings.signInTitle)
        }
    }
}

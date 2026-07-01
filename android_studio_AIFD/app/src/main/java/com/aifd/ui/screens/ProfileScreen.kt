package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.aifd.data.CloudApi
import com.aifd.data.UserProfile
import com.aifd.ui.localization.AppLocalizations
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    userProfile: UserProfile,
    onSave: (UserProfile) -> Unit,
    onBack: () -> Unit
) {
    val strings = AppLocalizations.strings
    val scope = rememberCoroutineScope()
    var isEditing by remember { mutableStateOf(false) }
    var isSaving  by remember { mutableStateOf(false) }
    var saveError by remember { mutableStateOf("") }

    var username      by remember { mutableStateOf(userProfile.username) }
    var caregiverName by remember { mutableStateOf(userProfile.caregiverName) }
    var wearerName    by remember { mutableStateOf(userProfile.wearerName) }
    var wearerBornYear by remember { mutableStateOf(userProfile.wearerBornYear) }
    var wearerGender  by remember { mutableStateOf(userProfile.wearerGender) }
    var caregiverPhone by remember { mutableStateOf(userProfile.caregiverPhone) }

    // Load fresh profile from DB when screen opens
    LaunchedEffect(userProfile.username) {
        if (userProfile.username.isNotBlank()) {
            val result = withContext(Dispatchers.IO) { CloudApi.getProfile(userProfile.username) }
            if (result.ok) {
                caregiverName  = result.caregiverName
                wearerName     = result.wearerName
                wearerBornYear = result.wearerBornYear
                wearerGender   = result.wearerGender
                caregiverPhone = result.caregiverPhone
            }
        }
    }

    fun doSave() {
        val newProfile = UserProfile(
            username       = username,
            caregiverName  = caregiverName,
            caregiverPhone = caregiverPhone,
            wearerName     = wearerName,
            wearerBornYear = wearerBornYear,
            wearerGender   = wearerGender
        )
        isSaving  = true
        saveError = ""
        scope.launch {
            val result = withContext(Dispatchers.IO) { CloudApi.updateProfile(newProfile) }
            isSaving = false
            if (result.ok) {
                onSave(newProfile)
                isEditing = false
            } else {
                saveError = "Lưu thất bại: ${result.error}"
            }
        }
    }

    // Spinning icon for save loading state
    val spinTransition = rememberInfiniteTransition(label = "save_spin")
    val spinAngle by spinTransition.animateFloat(
        initialValue = 0f, targetValue = 360f,
        animationSpec = infiniteRepeatable(tween(700, easing = LinearEasing)),
        label = "spin_angle"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(strings.profile) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = strings.back)
                    }
                },
                actions = {
                    if (isEditing) {
                        if (isSaving) {
                            IconButton(onClick = {}) {
                                Icon(Icons.Default.Refresh, null, modifier = Modifier.size(20.dp).rotate(spinAngle))
                            }
                        } else {
                            TextButton(onClick = { doSave() }) {
                                Text(strings.save, fontWeight = FontWeight.Bold)
                            }
                        }
                    } else {
                        IconButton(onClick = { isEditing = true; saveError = "" }) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit Profile")
                        }
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Avatar & username
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Surface(
                    modifier = Modifier.size(80.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Icon(
                        Icons.Default.Person,
                        contentDescription = null,
                        modifier = Modifier.padding(16.dp).fillMaxSize(),
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
                Spacer(Modifier.height(16.dp))
                if (isEditing) {
                    OutlinedTextField(
                        value = username,
                        onValueChange = { username = it },
                        label = { Text(strings.username) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                } else {
                    Text(text = username, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                }
            }

            Divider(color = MaterialTheme.colorScheme.outlineVariant)

            // Caregiver section
            ProfileInfoItem(strings.caregiverNameLabel, caregiverName, isEditing) { caregiverName = it }
            ProfileInfoItem(strings.caregiverPhoneLabel, caregiverPhone, isEditing, KeyboardType.Phone) { caregiverPhone = it }

            Divider(color = MaterialTheme.colorScheme.outlineVariant)

            // Wearer section
            ProfileInfoItem(strings.wearerNameLabel, wearerName, isEditing) { wearerName = it }
            ProfileInfoItem(strings.wearerAgeLabel, wearerBornYear, isEditing, KeyboardType.Number) { wearerBornYear = it }

            // Gender
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = strings.wearerGenderLabel,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(6.dp))
                if (isEditing) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("male" to strings.male, "female" to strings.female).forEach { (value, label) ->
                            FilterChip(
                                selected = wearerGender == value,
                                onClick = { wearerGender = value },
                                label = { Text(label) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                } else {
                    Text(
                        text = strings.genderDisplay(wearerGender).ifBlank { strings.unknown },
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            if (saveError.isNotBlank()) {
                Text(saveError, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(80.dp))
        }
    }
}

@Composable
private fun ProfileInfoItem(
    label: String,
    value: String,
    isEditing: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text,
    onValueChange: (String) -> Unit = {}
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(Modifier.height(4.dp))
        if (isEditing) {
            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                textStyle = MaterialTheme.typography.bodyLarge,
                keyboardOptions = KeyboardOptions(keyboardType = keyboardType)
            )
        } else {
            Text(
                text = value.ifBlank { AppLocalizations.strings.unknown },
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

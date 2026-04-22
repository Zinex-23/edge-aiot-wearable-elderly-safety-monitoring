package com.aifd.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aifd.data.UserProfile
import com.aifd.ui.localization.AppLocalizations

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    userProfile: UserProfile,
    onSave: (UserProfile) -> Unit,
    onBack: () -> Unit
) {
    val strings = AppLocalizations.strings
    var isEditing by remember { mutableStateOf(false) }

    // Editable states
    var username by remember { mutableStateOf(userProfile.username) }
    var caregiverName by remember { mutableStateOf(userProfile.caregiverName) }
    var wearerName by remember { mutableStateOf(userProfile.wearerName) }
    var wearerAge by remember { mutableStateOf(userProfile.wearerAge) }
    var wearerGender by remember { mutableStateOf(userProfile.wearerGender) }
    var caregiverPhone by remember { mutableStateOf(userProfile.caregiverPhone) }

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
                        TextButton(onClick = {
                            isEditing = false
                            onSave(
                                UserProfile(
                                    username = username,
                                    caregiverName = caregiverName,
                                    caregiverPhone = caregiverPhone,
                                    wearerName = wearerName,
                                    wearerAge = wearerAge,
                                    wearerGender = wearerGender
                                )
                            )
                        }) {
                            Text(strings.save, fontWeight = FontWeight.Bold)
                        }
                    } else {
                        IconButton(onClick = { isEditing = true }) {
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
            // Header
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Surface(
                    modifier = Modifier.size(80.dp),
                    shape = androidx.compose.foundation.shape.CircleShape,
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Icon(
                        Icons.Default.Person,
                        contentDescription = null,
                        modifier = Modifier
                            .padding(16.dp)
                            .fillMaxSize(),
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
                    Text(
                        text = username,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Divider(
                color = MaterialTheme.colorScheme.outlineVariant,
                thickness = 1.dp
            )

            // Info Sections
            ProfileInfoItem(strings.caregiverNameLabel, caregiverName, isEditing) { caregiverName = it }
            ProfileInfoItem(strings.caregiverPhoneLabel, caregiverPhone, isEditing) { caregiverPhone = it }
            
            Divider(
                color = MaterialTheme.colorScheme.outlineVariant,
                thickness = 1.dp
            )
            
            ProfileInfoItem(strings.wearerNameLabel, wearerName, isEditing) { wearerName = it }
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Box(modifier = Modifier.weight(1f)) {
                    ProfileInfoItem(strings.wearerAgeLabel, wearerAge, isEditing) { wearerAge = it }
                }
                Box(modifier = Modifier.weight(1f)) {
                    ProfileInfoItem(strings.wearerGenderLabel, wearerGender, isEditing) { wearerGender = it }
                }
            }
        }
    }
}

@Composable
private fun ProfileInfoItem(
    label: String,
    value: String,
    isEditing: Boolean = false,
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
                textStyle = MaterialTheme.typography.bodyLarge
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

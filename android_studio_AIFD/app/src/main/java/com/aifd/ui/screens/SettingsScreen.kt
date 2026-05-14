package com.aifd.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PhoneIphone
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.ConnectionStatus
import com.aifd.data.DeviceInfo
import com.aifd.data.MockDataProvider
import com.aifd.data.UserRole
import com.aifd.ui.components.SectionHeader
import com.aifd.ui.localization.AppLanguage
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AppThemeMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    role: UserRole,
    device: DeviceInfo? = null,
    themeMode: AppThemeMode = AppThemeMode.LIGHT,
    language: AppLanguage = AppLanguage.ENGLISH,
    onThemeModeChange: (AppThemeMode) -> Unit = {},
    onLanguageChange: (AppLanguage) -> Unit = {},
    onRoleChange: (UserRole?) -> Unit = {},
    onNavigateToBlePairing: () -> Unit = {},
    onNavigateToDeviceDetail: () -> Unit = {},
    onNavigateToEmergencyContacts: () -> Unit = {},
    onNavigateToNotifications: () -> Unit = {},
    onNavigateToAccount: () -> Unit = {},
    onLogout: () -> Unit = {},
    onClearData: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    var showLogoutDialog by remember { mutableStateOf(false) }
    var showThemeDialog by remember { mutableStateOf(false) }
    var showLanguageDialog by remember { mutableStateOf(false) }
    var showRoleDialog by remember { mutableStateOf(false) }
    var showClearDataDialog by remember { mutableStateOf(false) }

    val themeLabel = when (themeMode) {
        AppThemeMode.LIGHT -> strings.light
        AppThemeMode.DARK -> strings.dark
        AppThemeMode.SYSTEM -> strings.system
    }
    val languageLabel = when (language) {
        AppLanguage.ENGLISH -> strings.english
        AppLanguage.VIETNAMESE -> strings.vietnamese
    }
    val roleLabel = if (role == UserRole.WEARER) strings.wearer else strings.caregiver

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ElevatedCard {
            Column(modifier = Modifier.padding(vertical = 4.dp)) {
                SectionHeader(strings.appearance, Modifier.padding(horizontal = 16.dp))
                SettingsItem(
                    icon = Icons.Default.Palette,
                    label = strings.theme,
                    value = themeLabel,
                    onClick = { showThemeDialog = true }
                )
                SettingsItem(
                    icon = Icons.Default.Translate,
                    label = strings.language,
                    value = languageLabel,
                    onClick = { showLanguageDialog = true }
                )
                SettingsItem(
                    icon = Icons.Default.Person,
                    label = strings.role,
                    value = roleLabel,
                    onClick = { showRoleDialog = true }
                )
            }
        }



        ElevatedCard {
            Column(modifier = Modifier.padding(vertical = 4.dp)) {
                SectionHeader(strings.account, Modifier.padding(horizontal = 16.dp))
                SettingsItem(
                    icon = Icons.Default.Person,
                    label = strings.profile,
                    value = strings.viewProfile,
                    onClick = onNavigateToAccount
                )
            }
        }

        OutlinedButton(
            onClick = { showClearDataDialog = true },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = MaterialTheme.colorScheme.error
            )
        ) {
            Icon(Icons.Default.Delete, contentDescription = null,
                modifier = Modifier.padding(end = 8.dp))
            Text(strings.clearData, fontWeight = FontWeight.SemiBold)
        }

        OutlinedButton(
            onClick = { showLogoutDialog = true },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = MaterialTheme.colorScheme.error
            )
        ) {
            Text(strings.logout, fontWeight = FontWeight.SemiBold)
        }

        Text(
            text = "AIFD v1.0.0",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 24.dp)
                .wrapContentWidth(Alignment.CenterHorizontally)
        )
    }

    if (showThemeDialog) {
        SelectionDialog(
            title = strings.chooseTheme,
            options = listOf(
                strings.light to { onThemeModeChange(AppThemeMode.LIGHT) },
                strings.dark to { onThemeModeChange(AppThemeMode.DARK) },
                strings.system to { onThemeModeChange(AppThemeMode.SYSTEM) }
            ),
            selected = themeLabel,
            onDismiss = { showThemeDialog = false }
        )
    }

    if (showLanguageDialog) {
        SelectionDialog(
            title = strings.chooseLanguage,
            options = listOf(
                strings.english to { onLanguageChange(AppLanguage.ENGLISH) },
                strings.vietnamese to { onLanguageChange(AppLanguage.VIETNAMESE) }
            ),
            selected = languageLabel,
            onDismiss = { showLanguageDialog = false }
        )
    }

    if (showRoleDialog) {
        SelectionDialog(
            title = strings.switchRole,
            options = listOf(
                strings.wearer to { onRoleChange(UserRole.WEARER) },
                strings.caregiver to { onRoleChange(UserRole.CAREGIVER) }
            ),
            selected = roleLabel,
            onDismiss = { showRoleDialog = false }
        )
    }

    if (showClearDataDialog) {
        AlertDialog(
            onDismissRequest = { showClearDataDialog = false },
            title = { Text(strings.clearDataTitle) },
            text  = { Text(strings.clearDataMessage) },
            confirmButton = {
                TextButton(
                    onClick = {
                        showClearDataDialog = false
                        onClearData()
                    },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) { Text(strings.clearDataConfirm) }
            },
            dismissButton = {
                TextButton(onClick = { showClearDataDialog = false }) { Text(strings.cancel) }
            }
        )
    }

    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text(strings.logoutTitle) },
            text = { Text(strings.logoutMessage) },
            confirmButton = {
                TextButton(
                    onClick = {
                        showLogoutDialog = false
                        onLogout()
                    }
                ) { Text(strings.logout) }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutDialog = false }) { Text(strings.cancel) }
            }
        )
    }
}

@Composable
private fun SelectionDialog(
    title: String,
    options: List<Pair<String, () -> Unit>>,
    selected: String,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                options.forEach { (label, onClick) ->
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = MaterialTheme.shapes.medium,
                        color = if (label == selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                        onClick = {
                            onClick()
                            onDismiss()
                        }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 14.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(label, fontWeight = FontWeight.Medium)
                            if (label == selected) {
                                Icon(Icons.Default.Check, contentDescription = null)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(AppLocalizations.strings.cancel)
            }
        }
    )
}

@Composable
private fun SettingsToggleItem(
    icon: ImageVector,
    label: String,
    subtitle: String? = null,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onCheckedChange(!checked) }
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Surface(
            tonalElevation = 0.dp,
            modifier = Modifier.size(40.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            subtitle?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        androidx.compose.material3.Switch(
            checked = checked,
            onCheckedChange = onCheckedChange
        )
    }
}

@Composable
private fun SettingsItem(
    icon: ImageVector,
    label: String,
    value: String? = null,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Surface(
            tonalElevation = 0.dp,
            modifier = Modifier.size(40.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            value?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun SettingsScreenPreview() {
    AIFDTheme {
        SettingsScreen(
            role = UserRole.WEARER,
            device = MockDataProvider.device
        )
    }
}

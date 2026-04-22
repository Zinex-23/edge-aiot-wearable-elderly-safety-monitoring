package com.aifd.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aifd.data.UserRole
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDThemeExt

@Composable
fun RoleSelectionScreen(
    onRoleSelected: (UserRole) -> Unit
) {
    val strings = AppLocalizations.strings
    var selectedRole by remember { mutableStateOf<UserRole?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 28.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = strings.chooseRole,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = strings.roleIntro,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(24.dp))

        RoleCard(
            title = strings.wearer,
            description = strings.roleWearerSummary,
            icon = {
                Icon(Icons.Default.Bluetooth, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            },
            selected = selectedRole == UserRole.WEARER,
            onClick = { selectedRole = UserRole.WEARER }
        )

        Spacer(Modifier.height(16.dp))

        RoleCard(
            title = strings.caregiver,
            description = strings.roleCaregiverSummary,
            icon = {
                Icon(Icons.Default.Visibility, contentDescription = null, tint = AIFDThemeExt.colors.safe)
            },
            selected = selectedRole == UserRole.CAREGIVER,
            onClick = { selectedRole = UserRole.CAREGIVER }
        )

        Spacer(Modifier.height(24.dp))

        Button(
            onClick = { selectedRole?.let(onRoleSelected) },
            enabled = selectedRole != null,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(14.dp)
        ) {
            Icon(Icons.Default.Favorite, contentDescription = null)
            Spacer(Modifier.height(0.dp))
            Text(strings.continueLabel, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun RoleCard(
    title: String,
    description: String,
    icon: @Composable () -> Unit,
    selected: Boolean,
    onClick: () -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                icon()
            }
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

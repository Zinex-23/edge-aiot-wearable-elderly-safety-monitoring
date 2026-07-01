package com.aifd.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.ui.theme.AIFDTheme

/**
 * Section header label used to title groups of content.
 */
@Composable
fun SectionHeader(
    title: String,
    modifier: Modifier = Modifier
) {
    Text(
        text = title.uppercase(),
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Medium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        letterSpacing = MaterialTheme.typography.labelMedium.letterSpacing,
        modifier = modifier.padding(vertical = 8.dp)
    )
}

@Preview(showBackground = true)
@Composable
private fun SectionHeaderPreview() {
    AIFDTheme {
        SectionHeader(title = "Device")
    }
}

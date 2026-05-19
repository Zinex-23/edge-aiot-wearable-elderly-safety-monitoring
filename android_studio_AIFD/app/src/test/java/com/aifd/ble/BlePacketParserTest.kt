package com.aifd.ble

import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for the AIFD BLE CSV protocol parsers.
 * Pure JVM tests — no Android dependencies.
 */
class BlePacketParserTest {

    // ── classify ─────────────────────────────────────────────────────────

    @Test fun classify_recognisesAllKnownPrefixes() {
        assertEquals(BlePacketParser.PacketKind.ALERT, BlePacketParser.classify("ALERT,1,2,fall,1,0.9,0.1"))
        assertEquals(BlePacketParser.PacketKind.SAFE,  BlePacketParser.classify("SAFE,1,2"))
        assertEquals(BlePacketParser.PacketKind.BATCH, BlePacketParser.classify("BATCH,1,..."))
        assertEquals(BlePacketParser.PacketKind.BMI,   BlePacketParser.classify("BMI,1,2,1.0,5.0,0"))
    }

    @Test fun classify_unknownPrefixReturnsUnknown() {
        assertEquals(BlePacketParser.PacketKind.UNKNOWN, BlePacketParser.classify("XYZ,1"))
        assertEquals(BlePacketParser.PacketKind.UNKNOWN, BlePacketParser.classify(""))
        assertEquals(BlePacketParser.PacketKind.UNKNOWN, BlePacketParser.classify("no-comma"))
    }

    // ── parseAlert ───────────────────────────────────────────────────────

    @Test fun parseAlert_validFallPacket() {
        val r = BlePacketParser.parseAlert("ALERT,12,845,fall,1,0.873,0.127")
        assertNotNull(r); r!!
        assertEquals(12, r.sequence)
        assertEquals(845L, r.timestampSec)
        assertEquals("fall", r.prediction)
        assertEquals(1, r.statusCode)
        assertEquals(0.873f, r.fallProb, 1e-4f)
        assertEquals(0.127f, r.nonFallProb, 1e-4f)
    }

    @Test fun parseAlert_wrongPrefixReturnsNull() {
        assertNull(BlePacketParser.parseAlert("BATCH,1,2,3,4,5"))
    }

    @Test fun parseAlert_wrongFieldCountReturnsNull() {
        assertNull(BlePacketParser.parseAlert("ALERT,1,2,fall,1,0.9"))     // 6 fields
        assertNull(BlePacketParser.parseAlert("ALERT,1,2,fall,1,0.9,0.1,x")) // 8 fields
    }

    @Test fun parseAlert_nonNumericReturnsNull() {
        assertNull(BlePacketParser.parseAlert("ALERT,abc,2,fall,1,0.9,0.1"))
        assertNull(BlePacketParser.parseAlert("ALERT,1,2,fall,1,not_a_float,0.1"))
    }

    // ── parseSafe ────────────────────────────────────────────────────────

    @Test fun parseSafe_validPacket() {
        val r = BlePacketParser.parseSafe("SAFE,7,1234")
        assertNotNull(r); r!!
        assertEquals(7, r.first)
        assertEquals(1234L, r.second)
    }

    @Test fun parseSafe_malformedReturnsNull() {
        assertNull(BlePacketParser.parseSafe("SAFE,7"))
        assertNull(BlePacketParser.parseSafe("SAFE,7,abc"))
        assertNull(BlePacketParser.parseSafe("ALERT,7,1234"))
    }

    // ── parseBatch ───────────────────────────────────────────────────────

    @Test fun parseBatch_validPacket() {
        val r = BlePacketParser.parseBatch(
            "BATCH,31,72|74|75|73|76,98|98|97|98|97,810|815|820|825|830"
        )
        assertNotNull(r); r!!
        assertEquals(31, r.sequence)
        assertEquals(listOf(72, 74, 75, 73, 76), r.heartRates)
        assertEquals(listOf(98, 98, 97, 98, 97), r.spo2s)
        assertEquals(listOf(810L, 815L, 820L, 825L, 830L), r.timestamps)
    }

    @Test fun parseBatch_invalidSensorMarkerMappedToMinusOne() {
        val r = BlePacketParser.parseBatch(
            "BATCH,1,255|72|255|73|76,255|98|97|255|97,1|2|3|4|5"
        )
        assertNotNull(r); r!!
        assertEquals(listOf(-1, 72, -1, 73, 76), r.heartRates)
        assertEquals(listOf(-1, 98, 97, -1, 97), r.spo2s)
    }

    @Test fun parseBatch_wrongSampleCountReturnsNull() {
        assertNull(BlePacketParser.parseBatch("BATCH,1,72|74,98|98,1|2"))         // 2 samples
        assertNull(BlePacketParser.parseBatch("BATCH,1,72|74|75|73|76|77,98|98|97|98|97,1|2|3|4|5")) // 6 hr
    }

    @Test fun parseBatch_garbageReturnsNull() {
        assertNull(BlePacketParser.parseBatch("BATCH,abc,72|74|75|73|76,98|98|97|98|97,1|2|3|4|5"))
        assertNull(BlePacketParser.parseBatch("not a packet at all"))
    }

    // ── parseBmi ─────────────────────────────────────────────────────────

    @Test fun parseBmi_validPacket() {
        val r = BlePacketParser.parseBmi("BMI,5,123,1.250,67.5,1")
        assertNotNull(r); r!!
        assertEquals(5, r.sequence)
        assertEquals(123L, r.timestampSec)
        assertEquals(1.250f, r.peakAccG, 1e-4f)
        assertEquals(67.5f, r.peakGyroDps, 1e-4f)
        assertTrue(r.active)
    }

    @Test fun parseBmi_idleActiveFlag() {
        val r = BlePacketParser.parseBmi("BMI,1,1,0.98,3.0,0")
        assertNotNull(r); r!!
        assertFalse(r.active)
    }

    @Test fun parseBmi_malformedReturnsNull() {
        assertNull(BlePacketParser.parseBmi("BMI,1,1,0.98,3.0"))        // 5 fields
        assertNull(BlePacketParser.parseBmi("BMI,abc,1,0.98,3.0,0"))
        assertNull(BlePacketParser.parseBmi("BMI,1,1,not_a_float,3.0,0"))
        assertNull(BlePacketParser.parseBmi("BATCH,1,1,0.98,3.0,0"))
    }
}

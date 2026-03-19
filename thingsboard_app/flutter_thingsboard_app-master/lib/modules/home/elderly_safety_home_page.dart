import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:thingsboard_app/config/themes/app_colors.dart';
import 'package:thingsboard_app/config/themes/tb_text_styles.dart';
import 'package:thingsboard_app/locator.dart';
import 'package:thingsboard_app/thingsboard_client.dart';
import 'package:thingsboard_app/utils/services/entity_query_api.dart';
import 'package:thingsboard_app/utils/services/tb_client_service/i_tb_client_service.dart';

class ElderlySafetyHomePage extends StatefulWidget {
  const ElderlySafetyHomePage({super.key, this.linkedDashboard});

  final HomeDashboardInfo? linkedDashboard;

  @override
  State<ElderlySafetyHomePage> createState() => _ElderlySafetyHomePageState();
}

class _ElderlySafetyHomePageState extends State<ElderlySafetyHomePage> {
  late Future<ElderlySafetyOverview> _overviewFuture;
  final _timeFormat = DateFormat('HH:mm');

  @override
  void initState() {
    super.initState();
    _overviewFuture = _loadOverview();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      body: RefreshIndicator(
        color: const Color(0xFF0F766E),
        onRefresh: _refresh,
        child: FutureBuilder<ElderlySafetyOverview>(
          future: _overviewFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return _LoadingView(linkedDashboard: widget.linkedDashboard);
            }
            if (snapshot.hasError) {
              return _ErrorView(
                linkedDashboard: widget.linkedDashboard,
                onRetry: _refresh,
                message: snapshot.error.toString(),
              );
            }
            final overview = snapshot.data!;
            return _OverviewView(
              overview: overview,
              linkedDashboard: widget.linkedDashboard,
              timeFormat: _timeFormat,
              onRefresh: _refresh,
            );
          },
        ),
      ),
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _overviewFuture = _loadOverview();
    });
    await _overviewFuture;
  }

  Future<ElderlySafetyOverview> _loadOverview() async {
    final tbClient = getIt<ITbClientService>().client;
    final devicePage = await tbClient.getEntityQueryService().findEntityDataByQuery(
      EntityDataQuery(
        entityFilter: EntityTypeFilter(entityType: EntityType.DEVICE),
        entityFields: EntityQueryApi.defaultDeviceFields,
        latestValues: [
          ...EntityQueryApi.defaultDeviceAttributes,
          ..._telemetryKeys,
        ],
        pageLink: EntityDataPageLink(
          pageSize: 12,
          sortOrder: EntityDataSortOrder(
            key: EntityKey(type: EntityKeyType.ENTITY_FIELD, key: 'createdTime'),
            direction: EntityDataSortOrderDirection.DESC,
          ),
        ),
      ),
    );

    final alarmPage = await tbClient.getAlarmService().getAllAlarmsV2(
      AlarmQueryV2(
        TimePageLink(
          8,
          0,
          null,
          SortOrder('createdTime', Direction.DESC),
        ),
        statusList: [AlarmSearchStatus.ACTIVE],
      ),
    );

    final alarms = List<AlarmInfo>.from(alarmPage.data)
      ..sort((a, b) {
        final severityDiff = _severityWeight(b.severity) - _severityWeight(a.severity);
        if (severityDiff != 0) {
          return severityDiff;
        }
        return (b.createdTime ?? 0).compareTo(a.createdTime ?? 0);
      });

    final devices =
        devicePage.data
            .map((entity) => ElderlyMonitoredDevice.fromEntity(entity, alarms))
            .toList()
          ..sort((a, b) {
            if (a.needsAttention != b.needsAttention) {
              return a.needsAttention ? -1 : 1;
            }
            final aTime = a.lastTelemetryAt?.millisecondsSinceEpoch ?? 0;
            final bTime = b.lastTelemetryAt?.millisecondsSinceEpoch ?? 0;
            return bTime.compareTo(aTime);
          });

    return ElderlySafetyOverview(
      generatedAt: DateTime.now(),
      devices: devices,
      activeAlarms: alarms,
    );
  }

  List<EntityKey> get _telemetryKeys {
    return const [
      'heartRate',
      'heart_rate',
      'hr',
      'pulse',
      'spo2',
      'SpO2',
      'oxygenSaturation',
      'blood_oxygen',
      'fallDetected',
      'fall_detected',
      'fall',
      'fallAlert',
      'isFall',
      'battery',
      'batteryLevel',
      'temperature',
      'bodyTemperature',
    ]
        .map((key) => EntityKey(type: EntityKeyType.TIME_SERIES, key: key))
        .toList();
  }
}

class ElderlySafetyOverview {
  const ElderlySafetyOverview({
    required this.generatedAt,
    required this.devices,
    required this.activeAlarms,
  });

  final DateTime generatedAt;
  final List<ElderlyMonitoredDevice> devices;
  final List<AlarmInfo> activeAlarms;

  int get connectedDevices => devices.where((device) => device.isConnected).length;

  int get devicesNeedingAttention =>
      devices.where((device) => device.needsAttention).length;

  AlarmInfo? get topAlarm => activeAlarms.isEmpty ? null : activeAlarms.first;

  ElderlyMonitoredDevice? get featuredDevice {
    for (final device in devices) {
      if (device.hasFallEmergency || device.activeAlarm != null) {
        return device;
      }
    }
    return devices.isEmpty ? null : devices.first;
  }
}

class ElderlyMonitoredDevice {
  ElderlyMonitoredDevice({
    required this.id,
    required this.name,
    required this.type,
    required this.label,
    required this.isConnected,
    required this.lastTelemetryAt,
    required this.heartRate,
    required this.spo2,
    required this.battery,
    required this.bodyTemperature,
    required this.fallDetected,
    required this.activeAlarm,
  });

  factory ElderlyMonitoredDevice.fromEntity(
    EntityData entity,
    List<AlarmInfo> alarms,
  ) {
    final latestTimeseries = entity.latest[EntityKeyType.TIME_SERIES] ?? const {};
    DateTime? lastTelemetryAt;
    for (final item in latestTimeseries.values) {
      final candidate = DateTime.fromMillisecondsSinceEpoch(item.ts);
      if (lastTelemetryAt == null || candidate.isAfter(lastTelemetryAt)) {
        lastTelemetryAt = candidate;
      }
    }

    final activeAlarm = _findDeviceAlarm(entity, alarms);
    final isConnected =
        entity.attribute('active') == 'true' ||
        (lastTelemetryAt != null &&
            DateTime.now().difference(lastTelemetryAt).inMinutes <= 10);

    return ElderlyMonitoredDevice(
      id: entity.entityId.id ?? '',
      name: entity.field('name') ?? 'Unknown device',
      type: entity.field('type') ?? 'Unknown type',
      label: entity.field('label'),
      isConnected: isConnected,
      lastTelemetryAt: lastTelemetryAt,
      heartRate: _readDouble(entity, const ['heartRate', 'heart_rate', 'hr', 'pulse']),
      spo2: _readDouble(
        entity,
        const ['spo2', 'SpO2', 'oxygenSaturation', 'blood_oxygen'],
      ),
      battery: _readDouble(entity, const ['battery', 'batteryLevel'])?.round(),
      bodyTemperature: _readDouble(
        entity,
        const ['temperature', 'bodyTemperature'],
      ),
      fallDetected: _readBool(
            entity,
            const ['fallDetected', 'fall_detected', 'fall', 'fallAlert', 'isFall'],
          ) ||
          _looksLikeFallAlarm(activeAlarm),
      activeAlarm: activeAlarm,
    );
  }

  final String id;
  final String name;
  final String type;
  final String? label;
  final bool isConnected;
  final DateTime? lastTelemetryAt;
  final double? heartRate;
  final double? spo2;
  final int? battery;
  final double? bodyTemperature;
  final bool fallDetected;
  final AlarmInfo? activeAlarm;

  bool get hasFallEmergency => fallDetected;

  bool get heartRateOutOfRange =>
      heartRate != null && (heartRate! < 55 || heartRate! > 110);

  bool get spo2OutOfRange => spo2 != null && spo2! < 94;

  bool get needsAttention =>
      hasFallEmergency ||
      activeAlarm != null ||
      !isConnected ||
      heartRateOutOfRange ||
      spo2OutOfRange;

  String get displayName => label?.trim().isNotEmpty == true ? label! : name;

  String get statusLabel {
    if (hasFallEmergency) {
      return 'Emergency';
    }
    if (activeAlarm != null || heartRateOutOfRange || spo2OutOfRange) {
      return 'Needs attention';
    }
    if (!isConnected) {
      return 'Device offline';
    }
    return 'Stable';
  }

  Color get accentColor {
    if (hasFallEmergency) {
      return const Color(0xFFD92D20);
    }
    if (activeAlarm != null || heartRateOutOfRange || spo2OutOfRange) {
      return const Color(0xFFB54708);
    }
    if (!isConnected) {
      return const Color(0xFF475467);
    }
    return const Color(0xFF027A48);
  }

  static AlarmInfo? _findDeviceAlarm(EntityData entity, List<AlarmInfo> alarms) {
    for (final alarm in alarms) {
      if (alarm.originator.id == entity.entityId.id) {
        return alarm;
      }
    }
    return null;
  }

  static bool _looksLikeFallAlarm(AlarmInfo? alarm) {
    final type = alarm?.type.toLowerCase();
    if (type == null) {
      return false;
    }
    return type.contains('fall') || type.contains('man down') || type.contains('sos');
  }

  static double? _readDouble(EntityData entity, List<String> keys) {
    final value = _readValue(entity, keys);
    if (value == null) {
      return null;
    }
    return double.tryParse(value.replaceAll(',', '.'));
  }

  static bool _readBool(EntityData entity, List<String> keys) {
    final value = _readValue(entity, keys);
    if (value == null) {
      return false;
    }
    final normalized = value.trim().toLowerCase();
    if (normalized == 'true' ||
        normalized == '1' ||
        normalized == 'yes' ||
        normalized == 'detected' ||
        normalized == 'alert') {
      return true;
    }
    final numeric = double.tryParse(normalized);
    return numeric != null && numeric > 0;
  }

  static String? _readValue(EntityData entity, List<String> keys) {
    final values = entity.latest[EntityKeyType.TIME_SERIES];
    if (values == null) {
      return null;
    }
    for (final key in keys) {
      final value = values[key]?.value;
      if (value != null && value.trim().isNotEmpty && value.trim() != 'null') {
        return value;
      }
    }
    return null;
  }
}

class _OverviewView extends StatelessWidget {
  const _OverviewView({
    required this.overview,
    required this.linkedDashboard,
    required this.timeFormat,
    required this.onRefresh,
  });

  final ElderlySafetyOverview overview;
  final HomeDashboardInfo? linkedDashboard;
  final DateFormat timeFormat;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final featuredDevice = overview.featuredDevice;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _HeroPanel(
          overview: overview,
          linkedDashboard: linkedDashboard,
          timeFormat: timeFormat,
        ),
        const SizedBox(height: 18),
        if (featuredDevice != null) ...[
          _SectionHeader(
            title: 'Priority monitor',
            subtitle: 'Live overview of the device that needs your attention first.',
          ),
          const SizedBox(height: 12),
          _FeaturedPatientCard(device: featuredDevice, timeFormat: timeFormat),
          const SizedBox(height: 18),
        ],
        _SectionHeader(
          title: 'Monitored devices',
          subtitle: 'Heart rate, SpO2 and fall status across your wearable fleet.',
          actionLabel: 'Devices',
          onAction: () => context.push('/devices'),
        ),
        const SizedBox(height: 12),
        if (overview.devices.isEmpty)
          const _EmptyCard(
            title: 'No devices found',
            description:
                'Connect your wearable device to ThingsBoard to start monitoring heart rate, SpO2 and fall alerts here.',
          )
        else
          ...overview.devices.map(
            (device) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _DeviceHealthCard(device: device, timeFormat: timeFormat),
            ),
          ),
        const SizedBox(height: 18),
        _SectionHeader(
          title: 'Active alerts',
          subtitle: 'Alarms surfaced from ThingsBoard that require review.',
          actionLabel: 'Alarms',
          onAction: () => context.push('/alarms'),
        ),
        const SizedBox(height: 12),
        if (overview.activeAlarms.isEmpty)
          const _EmptyCard(
            title: 'No active alerts',
            description:
                'Your monitoring space is currently stable. Pull to refresh for the latest telemetry and alarm state.',
          )
        else
          ...overview.activeAlarms.map(
            (alarm) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _AlarmCard(alarm: alarm, timeFormat: timeFormat),
            ),
          ),
        const SizedBox(height: 18),
        _SectionHeader(
          title: 'Quick actions',
          subtitle: 'Open the operational screens you will use during a live demo.',
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _QuickActionButton(
              icon: Icons.health_and_safety_outlined,
              label: 'Refresh',
              onTap: onRefresh,
            ),
            _QuickActionButton(
              icon: Icons.devices_other_outlined,
              label: 'Devices',
              onTap: () => context.push('/devices'),
            ),
            _QuickActionButton(
              icon: Icons.notification_important_outlined,
              label: 'Alarms',
              onTap: () => context.push('/alarms'),
            ),
            _QuickActionButton(
              icon: Icons.dashboard_customize_outlined,
              label: linkedDashboard != null ? 'Dashboards' : 'More',
              onTap: () => context.push(linkedDashboard != null ? '/dashboards' : '/more'),
            ),
          ],
        ),
      ],
    );
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel({
    required this.overview,
    required this.linkedDashboard,
    required this.timeFormat,
  });

  final ElderlySafetyOverview overview;
  final HomeDashboardInfo? linkedDashboard;
  final DateFormat timeFormat;

  @override
  Widget build(BuildContext context) {
    final topAlarm = overview.topAlarm;
    final topAlarmMessage =
        topAlarm == null
            ? 'No active emergency alarm. Telemetry is being monitored in real time.'
            : '${topAlarm.type} on ${topAlarm.originatorLabel ?? topAlarm.originatorName ?? 'device'}';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0F766E), Color(0xFF155EEF), Color(0xFF102A56)],
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF102A56).withValues(alpha: 0.22),
            blurRadius: 32,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AIoT Elderly Safety Monitor',
                      style: TbTextStyles.titleMedium.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'A native command center for wearable telemetry, oxygen saturation tracking and fall emergency detection.',
                      style: TbTextStyles.bodyMedium.copyWith(
                        color: Colors.white.withValues(alpha: 0.84),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(
                  Icons.monitor_heart_outlined,
                  color: Colors.white,
                  size: 28,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _HeroMetric(
                label: 'Monitored devices',
                value: overview.devices.length.toString(),
              ),
              _HeroMetric(
                label: 'Connected',
                value: overview.connectedDevices.toString(),
              ),
              _HeroMetric(
                label: 'Active alerts',
                value: overview.activeAlarms.length.toString(),
                accent: overview.activeAlarms.isEmpty
                    ? const Color(0xFFB7F6C6)
                    : const Color(0xFFFFD6AE),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: topAlarm == null
                        ? const Color(0xFFB7F6C6).withValues(alpha: 0.18)
                        : const Color(0xFFFFD6AE).withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    topAlarm == null
                        ? Icons.check_circle_outline
                        : Icons.warning_amber_rounded,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        topAlarm == null ? 'Current safety state' : 'Priority alert',
                        style: TbTextStyles.labelLarge.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        topAlarmMessage,
                        style: TbTextStyles.bodyMedium.copyWith(
                          color: Colors.white.withValues(alpha: 0.9),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(
                'Updated ${timeFormat.format(overview.generatedAt)}',
                style: TbTextStyles.bodySmall.copyWith(
                  color: Colors.white.withValues(alpha: 0.74),
                ),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: () => context.push(linkedDashboard != null ? '/dashboards' : '/more'),
                style: TextButton.styleFrom(
                  foregroundColor: Colors.white,
                  backgroundColor: Colors.white.withValues(alpha: 0.12),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                ),
                icon: const Icon(Icons.arrow_forward, size: 18),
                label: Text(linkedDashboard != null ? 'Open dashboards' : 'Open more'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({
    required this.label,
    required this.value,
    this.accent = Colors.white,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 132,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: TbTextStyles.titleSmall.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TbTextStyles.bodySmall.copyWith(
              color: Colors.white.withValues(alpha: 0.76),
            ),
          ),
        ],
      ),
    );
  }
}

class _FeaturedPatientCard extends StatelessWidget {
  const _FeaturedPatientCard({
    required this.device,
    required this.timeFormat,
  });

  final ElderlyMonitoredDevice device;
  final DateFormat timeFormat;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: device.accentColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(Icons.favorite_outline, color: device.accentColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      device.displayName,
                      style: TbTextStyles.titleXs.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      device.type,
                      style: TbTextStyles.bodySmall.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusBadge(
                label: device.statusLabel,
                color: device.accentColor,
              ),
            ],
          ),
          const SizedBox(height: 16),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.55,
            children: [
              _VitalTile(
                icon: Icons.monitor_heart_outlined,
                label: 'Heart rate',
                value: device.heartRate == null ? '--' : '${device.heartRate!.round()} bpm',
                hint: device.heartRateOutOfRange ? 'Out of safe range' : 'Current pulse',
                color: device.heartRateOutOfRange
                    ? const Color(0xFFD92D20)
                    : const Color(0xFF155EEF),
              ),
              _VitalTile(
                icon: Icons.bloodtype_outlined,
                label: 'SpO2',
                value: device.spo2 == null ? '--' : '${device.spo2!.toStringAsFixed(0)}%',
                hint: device.spo2OutOfRange ? 'Low oxygen saturation' : 'Blood oxygen',
                color: device.spo2OutOfRange
                    ? const Color(0xFFD92D20)
                    : const Color(0xFF0F766E),
              ),
              _VitalTile(
                icon: Icons.accessibility_new_outlined,
                label: 'Fall status',
                value: device.hasFallEmergency ? 'ALERT' : 'Stable',
                hint: device.hasFallEmergency ? 'Emergency attention needed' : 'No fall signal',
                color: device.hasFallEmergency
                    ? const Color(0xFFD92D20)
                    : const Color(0xFF027A48),
              ),
              _VitalTile(
                icon: Icons.battery_charging_full_outlined,
                label: 'Battery',
                value: device.battery == null ? '--' : '${device.battery}%',
                hint: device.isConnected ? 'Wearable connected' : 'Connectivity lost',
                color: device.isConnected
                    ? const Color(0xFF155EEF)
                    : const Color(0xFF475467),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _ContextChip(
                icon: Icons.wifi_tethering_outlined,
                text: device.isConnected ? 'Connected' : 'Offline',
              ),
              _ContextChip(
                icon: Icons.schedule_outlined,
                text: device.lastTelemetryAt == null
                    ? 'No telemetry timestamp'
                    : 'Last update ${timeFormat.format(device.lastTelemetryAt!)}',
              ),
              if (device.bodyTemperature != null)
                _ContextChip(
                  icon: Icons.thermostat_outlined,
                  text: '${device.bodyTemperature!.toStringAsFixed(1)} C',
                ),
              if (device.activeAlarm != null)
                _ContextChip(
                  icon: Icons.error_outline,
                  text: device.activeAlarm!.type,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DeviceHealthCard extends StatelessWidget {
  const _DeviceHealthCard({
    required this.device,
    required this.timeFormat,
  });

  final ElderlyMonitoredDevice device;
  final DateFormat timeFormat;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: device.accentColor.withValues(alpha: 0.14)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: device.accentColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(Icons.watch_outlined, color: device.accentColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      device.displayName,
                      style: TbTextStyles.labelLarge.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      device.name,
                      style: TbTextStyles.bodySmall.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusBadge(label: device.statusLabel, color: device.accentColor),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _MiniMetric(
                  label: 'Heart rate',
                  value: device.heartRate == null ? '--' : '${device.heartRate!.round()} bpm',
                ),
              ),
              Expanded(
                child: _MiniMetric(
                  label: 'SpO2',
                  value: device.spo2 == null ? '--' : '${device.spo2!.toStringAsFixed(0)}%',
                ),
              ),
              Expanded(
                child: _MiniMetric(
                  label: 'Fall',
                  value: device.hasFallEmergency ? 'Alert' : 'Stable',
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _ContextChip(
                icon: Icons.wifi_tethering_outlined,
                text: device.isConnected ? 'Connected' : 'Offline',
              ),
              if (device.battery != null)
                _ContextChip(
                  icon: Icons.battery_std_outlined,
                  text: '${device.battery}%',
                ),
              _ContextChip(
                icon: Icons.schedule_outlined,
                text: device.lastTelemetryAt == null
                    ? 'No timestamp'
                    : 'Updated ${timeFormat.format(device.lastTelemetryAt!)}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AlarmCard extends StatelessWidget {
  const _AlarmCard({
    required this.alarm,
    required this.timeFormat,
  });

  final AlarmInfo alarm;
  final DateFormat timeFormat;

  @override
  Widget build(BuildContext context) {
    final createdTime =
        alarm.createdTime == null
            ? null
            : DateTime.fromMillisecondsSinceEpoch(alarm.createdTime!);
    final severityColor = _alarmColor(alarm.severity);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: severityColor.withValues(alpha: 0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: severityColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(Icons.warning_amber_rounded, color: severityColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      alarm.type,
                      style: TbTextStyles.labelLarge.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      alarm.originatorDisplayName ??
                          alarm.originatorLabel ??
                          alarm.originatorName ??
                          'Unknown originator',
                      style: TbTextStyles.bodySmall.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusBadge(
                label: alarm.severity.toShortString(),
                color: severityColor,
              ),
            ],
          ),
          if (alarm.details != null) ...[
            const SizedBox(height: 12),
            Text(
              alarm.details.toString(),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TbTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _ContextChip(
                icon: Icons.notifications_active_outlined,
                text: alarm.status.toShortString().replaceAll('_', ' '),
              ),
              if (createdTime != null)
                _ContextChip(
                  icon: Icons.schedule_outlined,
                  text: 'Created ${timeFormat.format(createdTime)}',
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QuickActionButton extends StatelessWidget {
  const _QuickActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        width: 162,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFFE8ECF4)),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: const Color(0xFFEAF2FF),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: const Color(0xFF155EEF), size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: TbTextStyles.labelMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.subtitle,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TbTextStyles.titleXs.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: TbTextStyles.bodyMedium.copyWith(
                  color: AppColors.textTertiary,
                ),
              ),
            ],
          ),
        ),
        if (actionLabel != null && onAction != null)
          TextButton(
            onPressed: onAction,
            child: Text(actionLabel!),
          ),
      ],
    );
  }
}

class _MiniMetric extends StatelessWidget {
  const _MiniMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TbTextStyles.bodySmall.copyWith(color: AppColors.textTertiary),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TbTextStyles.labelLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _VitalTile extends StatelessWidget {
  const _VitalTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.hint,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final String hint;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const Spacer(),
          Text(
            label,
            style: TbTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TbTextStyles.titleXs.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            hint,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TbTextStyles.caption.copyWith(color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TbTextStyles.bodySmall.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _ContextChip extends StatelessWidget {
  const _ContextChip({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F7FA),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppColors.textTertiary),
          const SizedBox(width: 6),
          Text(
            text,
            style: TbTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({
    required this.title,
    required this.description,
  });

  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TbTextStyles.labelLarge.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            description,
            style: TbTextStyles.bodyMedium.copyWith(color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }
}

class _LoadingView extends StatelessWidget {
  const _LoadingView({required this.linkedDashboard});

  final HomeDashboardInfo? linkedDashboard;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _HeroPanel(
          overview: ElderlySafetyOverview(
            generatedAt: DateTime.utc(2025),
            devices: [],
            activeAlarms: [],
          ),
          linkedDashboard: linkedDashboard,
          timeFormat: DateFormat('HH:mm'),
        ),
        const SizedBox(height: 40),
        const Center(child: CircularProgressIndicator()),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.linkedDashboard,
    required this.onRetry,
    required this.message,
  });

  final HomeDashboardInfo? linkedDashboard;
  final Future<void> Function() onRetry;
  final String message;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _HeroPanel(
          overview: ElderlySafetyOverview(
            generatedAt: DateTime.utc(2025),
            devices: [],
            activeAlarms: [],
          ),
          linkedDashboard: linkedDashboard,
          timeFormat: DateFormat('HH:mm'),
        ),
        const SizedBox(height: 20),
        _EmptyCard(
          title: 'Unable to load monitoring overview',
          description: message,
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: const Text('Try again'),
        ),
      ],
    );
  }
}

int _severityWeight(AlarmSeverity severity) {
  return switch (severity) {
    AlarmSeverity.CRITICAL => 5,
    AlarmSeverity.MAJOR => 4,
    AlarmSeverity.MINOR => 3,
    AlarmSeverity.WARNING => 2,
    AlarmSeverity.INDETERMINATE => 1,
  };
}

Color _alarmColor(AlarmSeverity severity) {
  return switch (severity) {
    AlarmSeverity.CRITICAL => const Color(0xFFD92D20),
    AlarmSeverity.MAJOR => const Color(0xFFDC6803),
    AlarmSeverity.MINOR => const Color(0xFFF79009),
    AlarmSeverity.WARNING => const Color(0xFF12B76A),
    AlarmSeverity.INDETERMINATE => const Color(0xFF667085),
  };
}

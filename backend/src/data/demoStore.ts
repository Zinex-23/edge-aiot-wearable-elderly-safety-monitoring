import bcrypt from 'bcryptjs';
import { Types } from 'mongoose';

import { UserRole, UserStatus } from '../models/User';

interface DemoUser {
  id: string;
  username: string;
  passwordHash: string;
  displayName: string;
  role: UserRole;
  status: UserStatus;
  mustChangePassword: boolean;
}

interface DemoWearer {
  id: string;
  fullName: string;
  gender: string;
  dateOfBirth: Date | null;
  address: string;
  phone: string;
}

interface DemoDevice {
  id: string;
  deviceCode: string;
  serialNumber: string;
  model: string;
  firmwareVersion: string;
  wearerId: string | null;
  assignedUserIds: string[];
  primaryAssignedUserId: string | null;
  status: string;
  currentState: {
    connectionStatus: string;
    batteryLevel: number;
    lastSeenAt: Date | null;
    latestHealth: {
      heartRate: number | null;
      spo2: number | null;
      hrv: number | null;
      capturedAt: Date | null;
    };
    latestLocation: {
      label: string;
      lat: number | null;
      lng: number | null;
      capturedAt: Date | null;
    };
  };
  createdAt: Date;
  updatedAt: Date;
}

interface DemoDeviceWithWearer extends DemoDevice {
  wearer: DemoWearer | null;
}

let initialized = false;
let users: DemoUser[] = [];
let wearers: DemoWearer[] = [];
let devices: DemoDevice[] = [];

export async function initializeDemoStore() {
  if (initialized) {
    return;
  }

  const adminId = new Types.ObjectId().toString();
  const caregiverId = new Types.ObjectId().toString();
  const wearerId = new Types.ObjectId().toString();
  const deviceId = new Types.ObjectId().toString();
  const passwordHash = await bcrypt.hash('123456', 12);
  const now = new Date();

  users = [
    {
      id: adminId,
      username: 'admin',
      passwordHash,
      displayName: 'System Admin',
      role: 'ADMIN',
      status: 'ACTIVE',
      mustChangePassword: true,
    },
    {
      id: caregiverId,
      username: 'caregiver01',
      passwordHash,
      displayName: 'Caregiver 01',
      role: 'CAREGIVER',
      status: 'ACTIVE',
      mustChangePassword: true,
    },
  ];

  wearers = [
    {
      id: wearerId,
      fullName: 'Nguyen Thi Lan',
      gender: 'FEMALE',
      dateOfBirth: new Date('1948-05-10'),
      address: 'District 7, HCMC',
      phone: '0900000000',
    },
  ];

  devices = [
    {
      id: deviceId,
      deviceCode: 'DEV-0001',
      serialNumber: 'SN-ABC-123',
      model: 'ESP32-WEAR-V2',
      firmwareVersion: '2.1.0',
      wearerId,
      assignedUserIds: [caregiverId],
      primaryAssignedUserId: caregiverId,
      status: 'ACTIVE',
      currentState: {
        connectionStatus: 'ONLINE',
        batteryLevel: 76,
        lastSeenAt: now,
        latestHealth: {
          heartRate: 66,
          spo2: 95,
          hrv: 41,
          capturedAt: now,
        },
        latestLocation: {
          label: 'District 7, HCMC',
          lat: 10.73,
          lng: 106.71,
          capturedAt: now,
        },
      },
      createdAt: now,
      updatedAt: now,
    },
  ];

  initialized = true;
}

export async function findDemoUserByUsername(username: string) {
  await initializeDemoStore();
  return users.find((user) => user.username === username.toLowerCase().trim()) ?? null;
}

export async function findDemoUserById(id: string) {
  await initializeDemoStore();
  return users.find((user) => user.id === id) ?? null;
}

export async function listDemoDevicesForUser(params: { userId: string; role: UserRole }) {
  await initializeDemoStore();

  const filteredDevices = params.role === 'ADMIN'
      ? devices
      : devices.filter((device) => device.assignedUserIds.includes(params.userId));

  return filteredDevices.map((device) => attachWearer(device));
}

export async function findDemoDeviceByIdForUser(params: {
  userId: string;
  role: UserRole;
  deviceId: string;
}) {
  const devicesForUser = await listDemoDevicesForUser({
    userId: params.userId,
    role: params.role,
  });

  return devicesForUser.find((device) => device.id === params.deviceId) ?? null;
}

function attachWearer(device: DemoDevice): DemoDeviceWithWearer {
  return {
    ...device,
    wearer: wearers.find((wearer) => wearer.id === device.wearerId) ?? null,
  };
}

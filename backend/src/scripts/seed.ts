import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import mongoose from 'mongoose';

import { connectToDatabase } from '../config/db';
import { getDatabaseMode } from '../config/runtime';
import { initializeDemoStore } from '../data/demoStore';
import { DeviceModel } from '../models/Device';
import { UserModel } from '../models/User';
import { WearerModel } from '../models/Wearer';

dotenv.config();

async function seed() {
  await connectToDatabase();

  if (getDatabaseMode() == 'memory') {
    await initializeDemoStore();
    console.log('MongoDB unavailable. Demo in-memory data initialized instead.');
    console.log('Admin: admin / 123456');
    console.log('Caregiver: caregiver01 / 123456');
    return;
  }

  const passwordHash = await bcrypt.hash('123456', 12);

  const admin = await UserModel.findOneAndUpdate(
    { username: 'admin' },
    {
      username: 'admin',
      passwordHash,
      displayName: 'System Admin',
      role: 'ADMIN',
      status: 'ACTIVE',
      mustChangePassword: true,
    },
    {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    },
  ).select('+passwordHash');

  const caregiver = await UserModel.findOneAndUpdate(
    { username: 'caregiver01' },
    {
      username: 'caregiver01',
      passwordHash,
      displayName: 'Caregiver 01',
      role: 'CAREGIVER',
      status: 'ACTIVE',
      mustChangePassword: true,
    },
    {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    },
  ).select('+passwordHash');

  const wearer = await WearerModel.findOneAndUpdate(
    { fullName: 'Nguyen Thi Lan' },
    {
      fullName: 'Nguyen Thi Lan',
      dateOfBirth: new Date('1948-05-10'),
      gender: 'FEMALE',
      address: 'District 7, HCMC',
      phone: '0900000000',
      medicalSummary: 'Hypertension, Type 2 Diabetes',
      emergencyContacts: [
        {
          name: 'Tran Van A',
          phone: '0911111111',
          relation: 'Son',
        },
      ],
      status: 'ACTIVE',
    },
    {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    },
  );

  await DeviceModel.findOneAndUpdate(
    { deviceCode: 'DEV-0001' },
    {
      deviceCode: 'DEV-0001',
      serialNumber: 'SN-ABC-123',
      model: 'ESP32-WEAR-V2',
      firmwareVersion: '2.1.0',
      wearerId: wearer._id,
      assignedUserIds: [caregiver._id],
      primaryAssignedUserId: caregiver._id,
      status: 'ACTIVE',
      currentState: {
        connectionStatus: 'ONLINE',
        batteryLevel: 76,
        lastSeenAt: new Date(),
        latestHealth: {
          heartRate: 66,
          spo2: 95,
          hrv: 41,
          capturedAt: new Date(),
        },
        latestLocation: {
          label: 'District 7, HCMC',
          lat: 10.73,
          lng: 106.71,
          capturedAt: new Date(),
        },
      },
    },
    {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    },
  );

  console.log('Seed completed successfully.');
  console.log(`Admin: ${admin.username} / 123456`);
  console.log(`Caregiver: ${caregiver.username} / 123456`);
}

seed()
  .catch((error) => {
    console.error('Seed failed:', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await mongoose.disconnect();
  });

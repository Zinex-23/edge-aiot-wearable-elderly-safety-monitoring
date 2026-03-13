import { Response } from 'express';
import { FilterQuery, Types } from 'mongoose';

import { isMongoMode } from '../config/runtime';
import {
  findDemoDeviceByIdForUser,
  listDemoDevicesForUser,
} from '../data/demoStore';
import { AuthenticatedRequest } from '../middlewares/auth.middleware';
import { Device, DeviceDocument, DeviceModel } from '../models/Device';

function buildScopeFilter(request: AuthenticatedRequest): FilterQuery<Device> {
  if (!request.auth) {
    return { _id: null };
  }

  if (request.auth.role === 'ADMIN') {
    return {};
  }

  return {
    assignedUserIds: new Types.ObjectId(request.auth.userId),
  };
}

function mapDevice(document: DeviceDocument | null) {
  if (!document) {
    return null;
  }

  const object = document.toObject({
    versionKey: false,
  }) as Device & {
    _id: Types.ObjectId;
    wearerId?: {
      _id: Types.ObjectId;
      fullName: string;
      gender: string;
      dateOfBirth: Date | null;
      phone: string;
    } | null;
  };

  return {
    id: object._id.toString(),
    deviceCode: object.deviceCode,
    serialNumber: object.serialNumber,
    model: object.model,
    firmwareVersion: object.firmwareVersion,
    status: object.status,
    wearer: object.wearerId
        ? {
            id: object.wearerId._id.toString(),
            fullName: object.wearerId.fullName,
            gender: object.wearerId.gender,
            dateOfBirth: object.wearerId.dateOfBirth,
            phone: object.wearerId.phone,
          }
        : null,
    assignedUserIds: object.assignedUserIds.map((value) => value.toString()),
    primaryAssignedUserId: object.primaryAssignedUserId?.toString() ?? null,
    currentState: {
      connectionStatus: object.currentState.connectionStatus,
      batteryLevel: object.currentState.batteryLevel,
      lastSeenAt: object.currentState.lastSeenAt,
      latestHealth: object.currentState.latestHealth,
      latestLocation: object.currentState.latestLocation,
    },
    createdAt: object.createdAt,
    updatedAt: object.updatedAt,
  };
}

export async function getMyDevices(req: AuthenticatedRequest, res: Response) {
  if (!req.auth) {
    return res.status(401).json({ message: 'Authentication is required.' });
  }

  if (!isMongoMode()) {
    const devices = await listDemoDevicesForUser({
      userId: req.auth.userId,
      role: req.auth.role,
    });

    return res.json({
      items: devices.map((device) => mapDemoDevice(device)),
      mode: 'memory',
    });
  }

  const devices = await DeviceModel.find(buildScopeFilter(req))
    .populate('wearerId', 'fullName gender dateOfBirth phone')
    .sort({ 'currentState.lastSeenAt': -1, createdAt: -1 });

  return res.json({
    items: devices.map((device) => mapDevice(device)),
    mode: 'mongo',
  });
}

export async function getDeviceById(req: AuthenticatedRequest, res: Response) {
  if (!req.auth) {
    return res.status(401).json({ message: 'Authentication is required.' });
  }

  const deviceId = req.params.id;

  if (isMongoMode() && !Types.ObjectId.isValid(deviceId)) {
    return res.status(400).json({ message: 'Invalid device id.' });
  }

  if (!isMongoMode()) {
    const device = await findDemoDeviceByIdForUser({
      userId: req.auth.userId,
      role: req.auth.role,
      deviceId,
    });

    if (!device) {
      return res.status(404).json({ message: 'Device not found.' });
    }

    return res.json({
      item: mapDemoDevice(device),
      mode: 'memory',
    });
  }

  const device = await DeviceModel.findOne({
    _id: new Types.ObjectId(deviceId),
    ...buildScopeFilter(req),
  }).populate('wearerId', 'fullName gender dateOfBirth phone');

  if (!device) {
    return res.status(404).json({ message: 'Device not found.' });
  }

  return res.json({
    item: mapDevice(device),
    mode: 'mongo',
  });
}

function mapDemoDevice(device: Awaited<ReturnType<typeof listDemoDevicesForUser>>[number]) {
  return {
    id: device.id,
    deviceCode: device.deviceCode,
    serialNumber: device.serialNumber,
    model: device.model,
    firmwareVersion: device.firmwareVersion,
    status: device.status,
    wearer: device.wearer
        ? {
            id: device.wearer.id,
            fullName: device.wearer.fullName,
            gender: device.wearer.gender,
            dateOfBirth: device.wearer.dateOfBirth,
            phone: device.wearer.phone,
          }
        : null,
    assignedUserIds: device.assignedUserIds,
    primaryAssignedUserId: device.primaryAssignedUserId,
    currentState: device.currentState,
    createdAt: device.createdAt,
    updatedAt: device.updatedAt,
  };
}

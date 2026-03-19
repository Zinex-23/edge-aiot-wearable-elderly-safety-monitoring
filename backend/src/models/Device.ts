import { HydratedDocument, Model, Schema, Types, model } from 'mongoose';

export type DeviceStatus = 'ACTIVE' | 'OFFLINE' | 'RETIRED';
export type ConnectionStatus = 'ONLINE' | 'OFFLINE';

interface LatestHealth {
  heartRate: number | null;
  spo2: number | null;
  hrv: number | null;
  capturedAt: Date | null;
}

interface LatestLocation {
  label: string;
  lat: number | null;
  lng: number | null;
  capturedAt: Date | null;
}

interface CurrentState {
  connectionStatus: ConnectionStatus;
  batteryLevel: number;
  lastSeenAt: Date | null;
  latestHealth: LatestHealth;
  latestLocation: LatestLocation;
}

export interface Device {
  deviceCode: string;
  serialNumber: string;
  model: string;
  firmwareVersion: string;
  wearerId: Types.ObjectId | null;
  assignedUserIds: Types.ObjectId[];
  primaryAssignedUserId: Types.ObjectId | null;
  status: DeviceStatus;
  currentState: CurrentState;
  createdAt: Date;
  updatedAt: Date;
}

type DeviceModel = Model<Device>;
export type DeviceDocument = HydratedDocument<Device>;

const latestHealthSchema = new Schema<LatestHealth>(
  {
    heartRate: { type: Number, default: null },
    spo2: { type: Number, default: null },
    hrv: { type: Number, default: null },
    capturedAt: { type: Date, default: null },
  },
  { _id: false },
);

const latestLocationSchema = new Schema<LatestLocation>(
  {
    label: { type: String, default: '', trim: true },
    lat: { type: Number, default: null },
    lng: { type: Number, default: null },
    capturedAt: { type: Date, default: null },
  },
  { _id: false },
);

const currentStateSchema = new Schema<CurrentState>(
  {
    connectionStatus: {
      type: String,
      enum: ['ONLINE', 'OFFLINE'],
      default: 'OFFLINE',
    },
    batteryLevel: {
      type: Number,
      default: 0,
      min: 0,
      max: 100,
    },
    lastSeenAt: {
      type: Date,
      default: null,
    },
    latestHealth: {
      type: latestHealthSchema,
      default: () => ({}),
    },
    latestLocation: {
      type: latestLocationSchema,
      default: () => ({}),
    },
  },
  { _id: false },
);

const deviceSchema = new Schema<Device, DeviceModel>(
  {
    deviceCode: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    serialNumber: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    model: {
      type: String,
      default: '',
      trim: true,
    },
    firmwareVersion: {
      type: String,
      default: '',
      trim: true,
    },
    wearerId: {
      type: Schema.Types.ObjectId,
      ref: 'Wearer',
      default: null,
    },
    assignedUserIds: {
      type: [{ type: Schema.Types.ObjectId, ref: 'User' }],
      default: [],
    },
    primaryAssignedUserId: {
      type: Schema.Types.ObjectId,
      ref: 'User',
      default: null,
    },
    status: {
      type: String,
      enum: ['ACTIVE', 'OFFLINE', 'RETIRED'],
      default: 'ACTIVE',
    },
    currentState: {
      type: currentStateSchema,
      default: () => ({}),
    },
  },
  {
    timestamps: true,
  },
);

deviceSchema.index({ assignedUserIds: 1, status: 1, 'currentState.lastSeenAt': -1 });
deviceSchema.index({ wearerId: 1 });

export const DeviceModel = model<Device, DeviceModel>('Device', deviceSchema);

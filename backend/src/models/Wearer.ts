import { HydratedDocument, Model, Schema, model } from 'mongoose';

export type WearerStatus = 'ACTIVE' | 'INACTIVE';
export type WearerGender = 'MALE' | 'FEMALE' | 'OTHER';

interface EmergencyContact {
  name: string;
  phone: string;
  relation: string;
}

export interface Wearer {
  fullName: string;
  dateOfBirth: Date | null;
  gender: WearerGender;
  address: string;
  phone: string;
  medicalSummary: string;
  emergencyContacts: EmergencyContact[];
  status: WearerStatus;
  createdAt: Date;
  updatedAt: Date;
}

type WearerModel = Model<Wearer>;
export type WearerDocument = HydratedDocument<Wearer>;

const emergencyContactSchema = new Schema<EmergencyContact>(
  {
    name: { type: String, required: true, trim: true },
    phone: { type: String, required: true, trim: true },
    relation: { type: String, required: true, trim: true },
  },
  { _id: false },
);

const wearerSchema = new Schema<Wearer, WearerModel>(
  {
    fullName: {
      type: String,
      required: true,
      trim: true,
    },
    dateOfBirth: {
      type: Date,
      default: null,
    },
    gender: {
      type: String,
      enum: ['MALE', 'FEMALE', 'OTHER'],
      required: true,
    },
    address: {
      type: String,
      required: true,
      trim: true,
    },
    phone: {
      type: String,
      default: '',
      trim: true,
    },
    medicalSummary: {
      type: String,
      default: '',
      trim: true,
    },
    emergencyContacts: {
      type: [emergencyContactSchema],
      default: [],
    },
    status: {
      type: String,
      enum: ['ACTIVE', 'INACTIVE'],
      default: 'ACTIVE',
    },
  },
  {
    timestamps: true,
  },
);

wearerSchema.index({ fullName: 1, status: 1 });

export const WearerModel = model<Wearer, WearerModel>('Wearer', wearerSchema);

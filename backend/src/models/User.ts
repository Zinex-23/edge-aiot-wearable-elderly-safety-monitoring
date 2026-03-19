import { HydratedDocument, Model, Schema, model } from 'mongoose';

export type UserRole = 'ADMIN' | 'CAREGIVER';
export type UserStatus = 'ACTIVE' | 'DISABLED';

export interface User {
  username: string;
  passwordHash: string;
  displayName: string;
  role: UserRole;
  status: UserStatus;
  mustChangePassword: boolean;
  createdAt: Date;
  updatedAt: Date;
}

type UserModel = Model<User>;
export type UserDocument = HydratedDocument<User>;

const userSchema = new Schema<User, UserModel>(
  {
    username: {
      type: String,
      required: true,
      unique: true,
      trim: true,
      lowercase: true,
    },
    passwordHash: {
      type: String,
      required: true,
      select: false,
    },
    displayName: {
      type: String,
      required: true,
      trim: true,
    },
    role: {
      type: String,
      enum: ['ADMIN', 'CAREGIVER'],
      required: true,
    },
    status: {
      type: String,
      enum: ['ACTIVE', 'DISABLED'],
      default: 'ACTIVE',
    },
    mustChangePassword: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
  },
);

userSchema.index({ role: 1, status: 1 });

export const UserModel = model<User, UserModel>('User', userSchema);

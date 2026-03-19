import bcrypt from 'bcryptjs';
import { Request, Response } from 'express';
import jwt from 'jsonwebtoken';

import { findDemoUserByUsername } from '../data/demoStore';
import { isMongoMode } from '../config/runtime';
import { UserModel } from '../models/User';

function buildAccessToken(params: { userId: string; username: string; role: 'ADMIN' | 'CAREGIVER' }) {
  const jwtSecret = process.env.JWT_SECRET;

  if (!jwtSecret) {
    throw new Error('JWT_SECRET is missing. Create backend/.env from backend/.env.example.');
  }

  return jwt.sign(
    {
      sub: params.userId,
      username: params.username,
      role: params.role,
    },
    jwtSecret,
    {
      expiresIn: '1d',
    },
  );
}

export async function login(req: Request, res: Response) {
  const { username, password } = req.body as {
    username?: string;
    password?: string;
  };

  if (!username || !password) {
    return res.status(400).json({ message: 'Username and password are required.' });
  }

  const user = isMongoMode()
      ? await UserModel.findOne({ username: username.toLowerCase().trim() }).select('+passwordHash')
      : await findDemoUserByUsername(username);

  if (!user || user.status !== 'ACTIVE') {
    return res.status(401).json({ message: 'Invalid username or password.' });
  }

  const isPasswordValid = await bcrypt.compare(password, user.passwordHash);

  if (!isPasswordValid) {
    return res.status(401).json({ message: 'Invalid username or password.' });
  }

  const accessToken = buildAccessToken({
    userId: user.id,
    username: user.username,
    role: user.role,
  });

  return res.json({
    accessToken,
    user: {
      id: user.id,
      username: user.username,
      displayName: user.displayName,
      role: user.role,
      status: user.status,
      mustChangePassword: user.mustChangePassword,
    },
  });
}

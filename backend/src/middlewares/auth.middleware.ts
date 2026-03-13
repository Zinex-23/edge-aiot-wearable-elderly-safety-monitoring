import { NextFunction, Request, Response } from 'express';
import jwt from 'jsonwebtoken';

import { isMongoMode } from '../config/runtime';
import { findDemoUserById } from '../data/demoStore';
import { UserRole, UserModel } from '../models/User';

export interface AuthContext {
  userId: string;
  username: string;
  role: UserRole;
}

export interface AuthenticatedRequest extends Request {
  auth?: AuthContext;
}

interface JwtPayload {
  sub: string;
  username: string;
  role: UserRole;
}

export async function authenticate(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ message: 'Missing Bearer token.' });
  }

  const token = authHeader.slice(7);
  const jwtSecret = process.env.JWT_SECRET;

  if (!jwtSecret) {
    return res.status(500).json({ message: 'JWT_SECRET is not configured.' });
  }

  try {
    const payload = jwt.verify(token, jwtSecret) as JwtPayload;
    const user = isMongoMode()
        ? await UserModel.findById(payload.sub).select('username role status')
        : await findDemoUserById(payload.sub);

    if (!user || user.status !== 'ACTIVE') {
      return res.status(401).json({ message: 'User is not allowed to access this resource.' });
    }

    req.auth = {
      userId: user.id,
      username: user.username,
      role: user.role,
    };

    return next();
  } catch (_error) {
    return res.status(401).json({ message: 'Invalid or expired token.' });
  }
}

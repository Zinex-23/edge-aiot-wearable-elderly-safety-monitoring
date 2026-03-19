import { NextFunction, Response } from 'express';

import { AuthenticatedRequest } from './auth.middleware';
import { UserRole } from '../models/User';

export function requireRole(...roles: UserRole[]) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.auth) {
      return res.status(401).json({ message: 'Authentication is required.' });
    }

    if (!roles.includes(req.auth.role)) {
      return res.status(403).json({ message: 'You do not have permission to perform this action.' });
    }

    return next();
  };
}

import { Router } from 'express';

import { getDeviceById, getMyDevices } from '../controllers/device.controller';
import { authenticate } from '../middlewares/auth.middleware';

const router = Router();

router.use(authenticate);
router.get('/my', getMyDevices);
router.get('/:id', getDeviceById);

export default router;

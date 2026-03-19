import dotenv from 'dotenv';

import app from './app';
import { connectToDatabase } from './config/db';

dotenv.config();

const port = Number(process.env.PORT || 3000);

async function bootstrap() {
  await connectToDatabase();

  app.listen(port, () => {
    console.log(`Backend is listening on port ${port}`);
  });
}

bootstrap().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});

import mongoose from 'mongoose';

import { setDatabaseMode } from './runtime';

export async function connectToDatabase() {
  const mongoUri = process.env.MONGODB_URI;

  if (!mongoUri) {
    setDatabaseMode('memory');
    console.warn('MONGODB_URI is missing. Backend will run in in-memory demo mode.');
    return;
  }

  try {
    await mongoose.connect(mongoUri);
    setDatabaseMode('mongo');
    console.log('Connected to MongoDB Atlas');
  } catch (error) {
    setDatabaseMode('memory');
    console.warn('MongoDB Atlas connection failed. Backend will run in in-memory demo mode.');
    console.warn(error instanceof Error ? error.message : error);
  }
}

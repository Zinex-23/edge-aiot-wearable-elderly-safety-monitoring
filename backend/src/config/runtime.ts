export type DatabaseMode = 'mongo' | 'memory';

let databaseMode: DatabaseMode = 'mongo';

export function setDatabaseMode(mode: DatabaseMode) {
  databaseMode = mode;
}

export function getDatabaseMode() {
  return databaseMode;
}

export function isMongoMode() {
  return databaseMode == 'mongo';
}

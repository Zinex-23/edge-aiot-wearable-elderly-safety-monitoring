import 'mongo_repository.dart';
import 'mongo_repository_web.dart'
    if (dart.library.io) 'mongo_repository_io.dart' as impl;

MongoRepository createMongoRepository() => impl.createMongoRepository();

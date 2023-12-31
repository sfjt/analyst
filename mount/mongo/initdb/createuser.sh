set -e
mongosh <<EOF
use admin
db.auth('$MONGO_INITDB_ROOT_USERNAME', '$MONGO_INITDB_ROOT_PASSWORD')

use $MONGO_INITDB_DATABASE
db.createUser({
  user: '$MONGO_INITDB_ANALYST_USERNAME',
  pwd: '$MONGO_INITDB_ANALYST_PASSWORD',
  roles: [{
    role: 'readWrite',
    db: '$MONGO_INITDB_DATABASE'
  }]
})
EOF

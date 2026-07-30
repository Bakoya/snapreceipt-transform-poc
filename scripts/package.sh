#!/bin/bash
set -e

echo "📦 Packaging Lambda deployment..."
cd "$(dirname "$0")/.."

rm -rf .build deployment.zip
mkdir -p .build

pip install -r requirements.txt -t .build --quiet \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all:

cp -r app .build/

cd .build
zip -r ../deployment.zip . -q
cd ..
rm -rf .build

echo "✅ deployment.zip created ($(du -h deployment.zip | cut -f1))"
echo ""
echo "Now deploy with:"
echo "  cd infra && terraform init && terraform apply"

#!/bin/bash

echo "🚀 COOLIFY SETUP FOR MAC STUDIO M3 ULTRA"
echo "════════════════════════════════════════════════════════"
echo ""
echo "This script will:"
echo "1. Install OrbStack (if not already installed)"
echo "2. Create Ubuntu VM for Coolify"
echo "3. Install Coolify in the VM"
echo ""
echo "Duration: ~5-10 minutes"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "📦 STEP 1: Installing OrbStack..."
echo "────────────────────────────────────────────────────────"

if command -v orb &> /dev/null; then
    echo "✅ OrbStack already installed!"
else
    echo "Installing OrbStack via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found!"
        echo "Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    brew install orbstack
    echo "✅ OrbStack installed!"
fi

echo ""
echo "🖥️  STEP 2: Creating Ubuntu VM..."
echo "────────────────────────────────────────────────────────"

# Check if VM already exists
if orb list | grep -q "coolify-server"; then
    echo "⚠️  VM 'coolify-server' already exists!"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        orb delete coolify-server -f
        echo "✅ Old VM deleted"
    else
        echo "Using existing VM..."
    fi
fi

if ! orb list | grep -q "coolify-server"; then
    echo "Creating Ubuntu VM 'coolify-server'..."
    orb create ubuntu coolify-server
    echo "✅ VM created!"
fi

echo ""
echo "⏳ Waiting for VM to be ready..."
sleep 5

echo ""
echo "🔧 STEP 3: Installing Coolify in VM..."
echo "────────────────────────────────────────────────────────"

echo "Connecting to VM and installing Coolify..."
echo "(This will take ~3-5 minutes)"
echo ""

# Install Coolify
ssh coolify-server << 'EOF'
echo "Installing Coolify..."
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

echo ""
echo "Waiting for Coolify to start..."
sleep 10

echo "Checking Coolify status..."
docker ps | grep coolify || echo "⚠️  Coolify containers not yet running (might need a minute)"
EOF

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ SETUP COMPLETE!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Access Coolify UI:"
echo "   http://localhost:8000"
echo ""
echo "2. SSH into VM (if needed):"
echo "   ssh coolify-server"
echo ""
echo "3. Check Coolify status:"
echo "   ssh coolify-server 'docker ps'"
echo ""
echo "4. View Coolify logs:"
echo "   ssh coolify-server 'docker logs coolify'"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "Share this info with Skipper-0! 🚀"
echo ""

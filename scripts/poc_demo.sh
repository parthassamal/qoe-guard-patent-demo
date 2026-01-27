#!/usr/bin/env bash
set -euo pipefail

# QoE-Guard POC Demo Script
# This script automates the complete POC demonstration flow

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
QOE_GUARD_URL="http://localhost:8010"
DEMO_TARGET_URL="http://localhost:8001"
MAX_WAIT_TIME=60

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     QoE-Aware JSON Variance Analytics System - POC        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a URL is accessible
check_url() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $name to be ready...${NC}"
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $name is ready${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    echo -e "${RED}✗ $name failed to start after $MAX_WAIT_TIME seconds${NC}"
    return 1
}

# Function to wait for Docker services
wait_for_docker() {
    echo -e "${BLUE}Step 1: Starting Docker services...${NC}"
    cd "$PROJECT_DIR"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed or not in PATH${NC}"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Start services
    echo "Building and starting containers..."
    docker compose up -d --build
    
    echo ""
    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 5
    
    # Check demo target service
    if ! check_url "$DEMO_TARGET_URL/play?v=1" "Demo Target Service"; then
        echo -e "${RED}Failed to start demo target service${NC}"
        docker compose logs demo-target
        exit 1
    fi
    
    # Check QoE-Guard service
    if ! check_url "$QOE_GUARD_URL" "QoE-Guard Service"; then
        echo -e "${RED}Failed to start QoE-Guard service${NC}"
        docker compose logs qoe-guard
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}✓ All services are running${NC}"
    echo ""
}

# Function to seed baseline
seed_baseline() {
    echo -e "${BLUE}Step 2: Seeding baseline scenario...${NC}"
    
    local response=$(curl -s "$QOE_GUARD_URL/seed")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Baseline scenario seeded${NC}"
    else
        echo -e "${YELLOW}⚠ Baseline seeding may have failed (this is OK if already seeded)${NC}"
    fi
    echo ""
}

# Function to run validation scenario
run_validation() {
    local version=$1
    local scenario_name=$2
    local expected_result=$3
    
    echo -e "${BLUE}Running validation: $scenario_name (v=$version)${NC}"
    
    local response=$(curl -s -L "$QOE_GUARD_URL/run?v=$version")
    
    if echo "$response" | grep -q "Internal Server Error"; then
        echo -e "${RED}✗ Validation failed with server error${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Validation completed${NC}"
    echo -e "  Expected result: ${YELLOW}$expected_result${NC}"
    echo ""
    return 0
}

# Function to display summary
display_summary() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    POC Demo Summary                       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Services are running:${NC}"
    echo -e "  • QoE-Guard UI:     ${YELLOW}$QOE_GUARD_URL${NC}"
    echo -e "  • Demo Target API:  ${YELLOW}$DEMO_TARGET_URL${NC}"
    echo ""
    echo -e "${GREEN}Demo Scenarios Available:${NC}"
    echo -e "  • v=1: Baseline (stable response)"
    echo -e "  • v=2: WARN scenario (moderate changes)"
    echo -e "  • v=3: PASS scenario (minor safe changes)"
    echo -e "  • v=4: FAIL scenario (breaking changes)"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo -e "  1. Open ${YELLOW}$QOE_GUARD_URL${NC} in your browser"
    echo -e "  2. Click 'Seed Baseline' to create initial scenario"
    echo -e "  3. Run validations using /run?v=2, /run?v=3, /run?v=4"
    echo -e "  4. Explore the reports and scoring results"
    echo -e "  5. Try the Swagger analyzer at ${YELLOW}$QOE_GUARD_URL/swagger${NC}"
    echo ""
    echo -e "${GREEN}API Endpoints:${NC}"
    echo -e "  • Seed baseline:    ${YELLOW}$QOE_GUARD_URL/seed${NC}"
    echo -e "  • Run validation:   ${YELLOW}$QOE_GUARD_URL/run?v=2${NC}"
    echo -e "  • View runs:        ${YELLOW}$QOE_GUARD_URL/runs${NC}"
    echo -e "  • API docs:         ${YELLOW}$QOE_GUARD_URL/docs${NC}"
    echo ""
    echo -e "${GREEN}To stop services:${NC}"
    echo -e "  ${YELLOW}cd $PROJECT_DIR && docker compose down${NC}"
    echo ""
}

# Function to run automated scenarios
run_automated_scenarios() {
    echo -e "${BLUE}Step 3: Running automated validation scenarios...${NC}"
    echo ""
    
    # Run PASS scenario (v=3)
    run_validation 3 "PASS - Minor Changes" "PASS"
    
    # Run WARN scenario (v=2)
    run_validation 2 "WARN - Moderate Changes" "WARN"
    
    # Run FAIL scenario (v=4)
    run_validation 4 "FAIL - Breaking Changes" "FAIL"
    
    echo -e "${GREEN}✓ All automated scenarios completed${NC}"
    echo ""
}

# Main execution
main() {
    # Check if services are already running
    if curl -s -f "$QOE_GUARD_URL" > /dev/null 2>&1 && \
       curl -s -f "$DEMO_TARGET_URL/play?v=1" > /dev/null 2>&1; then
        echo -e "${GREEN}Services are already running${NC}"
        echo ""
    else
        wait_for_docker
    fi
    
    seed_baseline
    
    # Ask if user wants to run automated scenarios
    echo -e "${YELLOW}Would you like to run automated validation scenarios? (y/n)${NC}"
    read -t 10 -r response || response="n"
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        run_automated_scenarios
    else
        echo -e "${YELLOW}Skipping automated scenarios${NC}"
        echo ""
    fi
    
    display_summary
}

# Run main function
main

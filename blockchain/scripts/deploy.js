const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying CloudCredInvoice contract...");
  
  // Deploy the contract
  const CloudCredInvoice = await hre.ethers.getContractFactory("CloudCredInvoice");
  const contract = await CloudCredInvoice.deploy();

  await contract.deployed();

  console.log("✅ CloudCredInvoice deployed to:", contract.address);
  console.log("🌐 Network:", hre.network.name);
  console.log("⛽ Gas used:", contract.deployTransaction.gasUsed?.toString() || "Unknown");
  
  // Save contract info for Python backend
  const fs = require('fs');
  const contractInfo = {
    address: contract.address,
    network: hre.network.name,
    chainId: hre.network.config.chainId || 1337,
    deployedAt: new Date().toISOString()
  };
  
  fs.writeFileSync('../backend/contract_info.json', JSON.stringify(contractInfo, null, 2));
  console.log("📄 Contract info saved to ../backend/contract_info.json");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
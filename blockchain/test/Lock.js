const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Lock", function () {
  it("Should deploy successfully", async function () {
    const Lock = await ethers.getContractFactory("Lock");
    const unlockTime = Math.floor(Date.now() / 1000) + 60; // 1 minute from now
    const lockedAmount = ethers.utils.parseEther("1");
    const lock = await Lock.deploy(unlockTime, { value: lockedAmount });
    await lock.deployed();
    expect(lock.address).to.not.be.undefined;
  });
});
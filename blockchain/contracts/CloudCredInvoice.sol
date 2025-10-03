// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CloudCredInvoice
 * @dev Smart contract for CloudCred freelancer invoice management
 * @author CloudCred Team
 */
contract CloudCredInvoice {
    
    // Invoice structure
    struct Invoice {
        string invoiceId;
        address freelancer;
        address client;
        uint256 amount;
        string description;
        bool approved;
        bool exists;
        uint256 createdAt;
        uint256 approvedAt;
    }
    
    // Storage mappings
    mapping(string => Invoice) public invoices;
    mapping(address => string[]) public freelancerInvoices;
    mapping(address => string[]) public clientInvoices;
    
    // Events for blockchain logging
    event InvoiceCreated(
        string indexed invoiceId,
        address indexed freelancer,
        address indexed client,
        uint256 amount,
        string description,
        uint256 timestamp
    );
    
    event InvoiceApproved(
        string indexed invoiceId,
        address indexed approver,
        uint256 timestamp
    );
    
    // Modifiers for access control
    modifier onlyClient(string memory _invoiceId) {
        require(invoices[_invoiceId].exists, "Invoice does not exist");
        require(invoices[_invoiceId].client == msg.sender, "Only client can approve");
        _;
    }
    
    modifier invoiceMustExist(string memory _invoiceId) {
        require(invoices[_invoiceId].exists, "Invoice does not exist");
        _;
    }
    
    /**
     * @dev Create a new invoice on blockchain
     */
    function createInvoice(
        string memory _invoiceId,
        address _freelancer,
        address _client,
        uint256 _amount,
        string memory _description
    ) external {
        require(!invoices[_invoiceId].exists, "Invoice already exists");
        require(_freelancer != address(0), "Invalid freelancer address");
        require(_client != address(0), "Invalid client address");
        require(_amount > 0, "Amount must be greater than 0");
        require(bytes(_description).length > 0, "Description cannot be empty");
        
        // Create invoice
        invoices[_invoiceId] = Invoice({
            invoiceId: _invoiceId,
            freelancer: _freelancer,
            client: _client,
            amount: _amount,
            description: _description,
            approved: false,
            exists: true,
            createdAt: block.timestamp,
            approvedAt: 0
        });
        
        // Add to user arrays for easy lookup
        freelancerInvoices[_freelancer].push(_invoiceId);
        clientInvoices[_client].push(_invoiceId);
        
        emit InvoiceCreated(
            _invoiceId,
            _freelancer,
            _client,
            _amount,
            _description,
            block.timestamp
        );
    }
    
    /**
     * @dev Approve an invoice (only by client)
     */
    function approveInvoice(string memory _invoiceId) 
        external 
        onlyClient(_invoiceId) 
    {
        require(!invoices[_invoiceId].approved, "Invoice already approved");
        
        invoices[_invoiceId].approved = true;
        invoices[_invoiceId].approvedAt = block.timestamp;
        
        emit InvoiceApproved(_invoiceId, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Get invoice details
     */
    function getInvoice(string memory _invoiceId) 
        external 
        view 
        invoiceMustExist(_invoiceId)
        returns (
            string memory invoiceId,
            address freelancer,
            address client,
            uint256 amount,
            string memory description,
            bool approved,
            uint256 createdAt,
            uint256 approvedAt
        ) 
    {
        Invoice storage invoice = invoices[_invoiceId];
        return (
            invoice.invoiceId,
            invoice.freelancer,
            invoice.client,
            invoice.amount,
            invoice.description,
            invoice.approved,
            invoice.createdAt,
            invoice.approvedAt
        );
    }
    
    /**
     * @dev Get all invoice IDs for a freelancer
     */
    function getFreelancerInvoices(address _freelancer) 
        external 
        view 
        returns (string[] memory) 
    {
        return freelancerInvoices[_freelancer];
    }
    
    /**
     * @dev Get all invoice IDs for a client
     */
    function getClientInvoices(address _client) 
        external 
        view 
        returns (string[] memory) 
    {
        return clientInvoices[_client];
    }
    
    /**
     * @dev Check if an invoice exists
     */
    function invoiceExists(string memory _invoiceId) 
        external 
        view 
        returns (bool) 
    {
        return invoices[_invoiceId].exists;
    }
}
# -*- coding: utf-8 -*-
from web3 import Web3 

import time 

from django.conf import settings

import os

import logging

logger = logging.getLogger(__name__)

from web3.exceptions import TimeExhausted as txn_timeout

class ChainContract:
    
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        file_path = os.path.join(current_dir, "contract_info.json")
        
        with open(file_path ,"r", encoding="utf-8") as f:
            import json
            contract_info = json.load(f)
            contract_address = contract_info["contract_address"]
            self.abi = contract_info["abi"]
        self.rpc_endpoint = settings.RPC_ENDPOINT
        self.private_key = settings.PRIVATE_KEY
        self.wallet_address = settings.WALLET_ADDRESS
        self.contract_address = Web3.to_checksum_address(contract_address if contract_info else settings.CONTRACT_ADDRESS)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_endpoint))

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

        # print(f"Connected: {self.w3.is_connected()}")
        # # print(f"Current block: {self.w3.eth.block_number}")
        # # print(f"Chain ID: {self.w3.eth.chain_id}")
        
        logger.info(f"Connected to blockchain: {self.w3.is_connected()}, Current block: {self.w3.eth.block_number}, Chain ID: {self.w3.eth.chain_id}")
             
    
    def store_data(self, cid, delay_seconds, done_retry=False):
        
        return self.store_data_to_blockchain(cid, delay_seconds, done_retry=False)
    
     
     
    def convertion2byte(self, data):
        """Convert data to bytes if it's a string, else return as is."""
        if isinstance(data, str):
            return data.encode('utf-8')
        return data   
    
    def convert2str(self, data):
        """Convert bytes to string if it's bytes, else return as is."""
        if isinstance(data, bytes):
            return data.decode('utf-8')
        return data 

    def store_data_to_blockchain(self, cid, delay_seconds, done_retry=False):
        try:
           
            cid_bytes = self.convertion2byte(cid)
            
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            tx = self.contract.functions.store(cid_bytes, int(delay_seconds)).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'gas': 600000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash,180)

            logger.info("\n--- Storage Confirmation ---")
            logger.info(f"Transaction hash: {self.w3.to_hex(tx_hash)}")

            # Decode the transaction input to verify what was stored
            tx = self.w3.eth.get_transaction(tx_hash)
            decoded_input = self.contract.decode_function_input(tx['input'])
            function_args = decoded_input[1]
            
            logger.info(f"Stored data: '{self.convert2str(cid_bytes)[0:7]}...' with unlock time: {delay_seconds} seconds")

            logger.info("--- End of Confirmation ---\n")

            return  self.w3.to_hex(tx_hash)
        
        except txn_timeout :
            logger.error(f"Timeout error ... letting txn to  get mined completely ")
            time.sleep(120)
            return 
        
        except Exception as e:
            logger.error(f"Error storing data: {str(e)}")
            if not done_retry:
                logger.info("Retrying...")
                return self.store_data(cid, delay_seconds, done_retry=True)
            else:
                logger.error("Retry failed.")
                return None

    def get_expired_data(self, done_retry=False):
        """Get expired CIDs using .caller for view-only contract interaction"""
        try:
            # Use .caller to call the view function
            cids = self.contract.functions.getExpired().call()
            logger.info(f"Expired CIDs retrieved: {[self.convert2str(cid)[:7] + '...' for cid in cids]}")  # Log first 7 characters of each CID for brevity


            for i in range(len(cids)):
                self.deleteExpired(cids[i])

            return {
                'cids': cids,
                'count': len(cids)
            }
            
        except txn_timeout :
            logger.error(f"Timeout  while retrieving expired data: {str(e)}")
            return {'expired_ids': [], 'cids': [], 'count': 0}
        

        except Exception as e:
            
            logger.error(f"Error calling getExpired via caller: {str(e)}")
            if not done_retry:
                logger.info("Retrying...")
                time.sleep(3)
                return self.get_expired_data(done_retry=True)
            return {'expired_ids': [], 'cids': [], 'count': 0}


    def deleteExpired(self, expired_id :bytes , done_retry=False):
        
        try:
            # Build and send transaction
            
            if expired_id is None:
                logger.warning("No expired ID provided for deletion.")
                return None
            
           
            expired_id = self.convertion2byte(expired_id)
            
            
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.expire(expired_id).build_transaction({
                'chainId':self.w3.eth.chain_id,  # Sepolia
                'gas': 600000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash,120)
            logger.info(f" expired CIDs deleted")
            return receipt
      
        except txn_timeout :
            logger.error(f"Timeout error letting txn to  get mined completely")
            time.sleep(120)
            return None
                   
        except Exception as e:    
            logger.error(f"Error retrieving expired data: {str(e)}")
            if not done_retry:
                logger.info ("Retrying...")
                return self.deleteExpired(expired_id,done_retry=True)
                     
    
# def test_contract():
    
#     try:
#         import random
        
#         import sys
        
#         import django
        
        
#         sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#         os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECHOME.settings')
#         django.setup() 
        
#         contract = ChainContract()
#         temp_data = [ f"testingfor{random.randint(10,40)}"  for _ in range(10)  ]
        
#         for case_no in range(1,4):
            
            
#             data=temp_data[case_no-1]
            
#             print(f"for case no. -:{case_no} " ,f"data is : {data} " , f"unlock time is : {int(data[10:])} ")
            
#             contract.store_data( data , int(data[10:]))
            
#             print(f"waiting for {int(data[10:])} seconds to check if data is expired and retrievable")
            
#             time.sleep(int(data[10:])+60)
            
#             print(contract.get_expired_data())
            
        
#     except  Exception as e :
#         logger.error(f"Error in test_contract: {str(e)}") 
          
        
#   # Initialize the contract instance at module level to ensure it's ready for use in tasks
# # test_contract()           
  
  
            

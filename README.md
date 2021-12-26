# eth-validator-duties
Show upcoming validator duties (attestations/block proposals/sync committee memberships)

## Usage
wget https://raw.githubusercontent.com/gunnim/eth-validator-duties/master/eth_validator_duties.py

python eth_validator_duties.py -h

python eth_validator_duties.py  &lt;space seperated validator indexes&gt;

#### Only search for attestations using specified beacon node
python eth_validator_duties.py  &lt;space seperated validator indexes&gt; -a -u http://127.0.0.1:5052

## Show example results
python test.py

## References and further reading
https://ethereum.github.io/beacon-APIs/#/

https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md

### Attestation script originally from pietjepuk
https://gist.github.com/pietjepuk2/eb021db978ad20bfd94dce485be63150

https://www.coincashew.com/coins/overview-eth/guide-or-how-to-setup-a-validator-on-eth2-mainnet/how-to-find-longest-attestation-slot-gap

import eth_validator_duties


def main(eth2_api_url):
    """
    Shows example output for an upcoming proposer first,
    sync committee membership next and attestations throughout.
    Perfect to test with Infura api f.x.
    """

    duties = eth_validator_duties.Duties(
        [1],
        eth2_api_url,
        False
    )

    node_sync_data = duties.api_get("node/syncing")["data"]
    if bool(node_sync_data["is_syncing"]):
        print("Beacon node currently syncing !")
        return

    head_slot = int(node_sync_data["head_slot"])
    epoch = head_slot // eth_validator_duties.Duties.SLOTS_PER_EPOCH

    upcoming_proposer = duties.api_get(
        f"validator/duties/proposer/{epoch + 1}"
    )["data"][-1]["validator_index"]

    duties = eth_validator_duties.Duties(
        [int(upcoming_proposer)],
        eth2_api_url,
        False
    )

    print()
    print("### Showing output for upcoming block proposer")
    print()
    duties.main()

    # Reset in case of slow requests
    node_sync_data = duties.api_get("node/syncing")["data"]
    head_slot = int(node_sync_data["head_slot"])
    epoch = head_slot // eth_validator_duties.Duties.SLOTS_PER_EPOCH

    upcoming_committee_member = duties.api_get(
        f"beacon/states/head/sync_committees?epoch={epoch}"
    )["data"]["validators"][-1]

    duties = eth_validator_duties.Duties(
        [int(upcoming_committee_member)],
        eth2_api_url,
        False
    )

    print()
    print("### Showing output for current sync committee membership")
    print()
    duties.main()

    # Reset in case of slow requests
    node_sync_data = duties.api_get("node/syncing")["data"]
    head_slot = int(node_sync_data["head_slot"])
    epoch = head_slot // eth_validator_duties.Duties.SLOTS_PER_EPOCH

    cur_committee_start_epoch = epoch // eth_validator_duties.Duties.EPOCHS_PER_COMMITTEE * 256
    next_committee_start_epoch = cur_committee_start_epoch + 256

    upcoming_committee_member = duties.api_get(
        f"beacon/states/head/sync_committees?epoch={next_committee_start_epoch}"
    )["data"]["validators"][0]
    upcoming_committee_member2 = duties.api_get(
        f"beacon/states/head/sync_committees?epoch={next_committee_start_epoch}"
    )["data"]["validators"][-1]

    duties = eth_validator_duties.Duties(
        [
            int(upcoming_committee_member),
            int(upcoming_committee_member2)
        ],
        eth2_api_url,
        False
    )

    print()
    print("### Showing output for upcoming sync committee membership")
    print()
    duties.main()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ensure correct working of duty searcher"
    )
    parser.add_argument(
        "-u",
        "--api-url",
        dest="api_url",
        type=str,
        default="http://127.0.0.1:5052/eth/v1/",
        help="Consensus/beacon node http api url")

    args = parser.parse_args()

    main(args.api_url)

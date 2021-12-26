#!/usr/bin/env python3
import json
import math
from datetime import datetime, timedelta

import requests


class Duties:

    GENESIS_TIMESTAMP = 1606824023
    SLOTS_PER_EPOCH = 32
    SECONDS_PER_SLOT = 12
    EPOCHS_PER_COMMITTEE = 256

    def __init__(self, validators_indices, eth2_api_url, attestations_only):
        self.validators_indices = validators_indices
        self.eth2_api_url = eth2_api_url
        self.attestations_only = attestations_only

    def api_get(self, endpoint):
        return requests.get(f"{self.eth2_api_url}{endpoint}").json()

    def api_post(self, endpoint, data):
        return requests.post(f"{self.eth2_api_url}{endpoint}", data).json()

    def filter_and_sort_data(self, head_slot, *args):
        data = {}

        for duties in args:
            for d in duties:
                # Proposer data is not filtered by our validators by default
                if int(d["validator_index"]) in self.validators_indices:
                    # Flatten data
                    data.setdefault(int(d["slot"]), []).append(
                        d["validator_index"])

        # Filter out historical
        return {k: v for k, v in sorted(data.items()) if k >= head_slot}

    def get_and_merge_data(self, url_stem, head_slot):
        epoch = head_slot // Duties.SLOTS_PER_EPOCH

        cur_epoch_data = self.api_get(
            f"{url_stem}/{epoch}"
        )["data"]
        try:
            next_epoch_data = self.api_get(
                f"{url_stem}/{epoch + 1}"
            )["data"]
        except KeyError:
            # https://github.com/ewasm/eth2.0-specs/blob/execution/specs/validator/0_beacon-chain-validator.md#lookahead
            print(
                "Unable to look ahead for duties, this is expected for some beacon nodes, searching current epoch")
            print(
                "Issue for Lighthouse proposer duties here: https://github.com/sigp/lighthouse/issues/2880")
            print()
            next_epoch_data = []

        return self.filter_and_sort_data(
            head_slot,
            cur_epoch_data,
            next_epoch_data)

    def post_and_merge_data(self, url_stem, head_slot):
        epoch = head_slot // Duties.SLOTS_PER_EPOCH

        cur_epoch_data = self.api_post(
            f"{url_stem}/{epoch}",
            json.dumps(self.validators_indices)
        )["data"]

        next_epoch_data = self.api_post(
            f"{url_stem}/{epoch + 1}",
            json.dumps(self.validators_indices)
        )["data"]

        return self.filter_and_sort_data(
            head_slot,
            cur_epoch_data,
            next_epoch_data)

    def main(self):

        node_sync_data = self.api_get("node/syncing")["data"]
        if bool(node_sync_data["is_syncing"]):
            print("Beacon node currently syncing !")
            return

        head_slot = int(node_sync_data["head_slot"])
        epoch = head_slot // Duties.SLOTS_PER_EPOCH

        if self.attestations_only == False:
            print(
                "Searching for upcoming proposals (This epoch and next, "
                f"<> {self.SECONDS_PER_SLOT * self.SLOTS_PER_EPOCH}s)")

            proposer_duties = self.get_and_merge_data(
                "validator/duties/proposer",
                head_slot)

            for slot, validators in proposer_duties.items():
                slot_start = datetime.fromtimestamp(
                    self.GENESIS_TIMESTAMP + slot * self.SECONDS_PER_SLOT)
                slot_end = slot_start + \
                    timedelta(seconds=self.SECONDS_PER_SLOT)

                print(
                    f"Proposal - {slot}/{slot // self.SLOTS_PER_EPOCH}"
                    f" - {slot_start.strftime('%H:%M:%S')} until {slot_end.strftime('%H:%M:%S')}"
                    # To support shared filter function w/ attestations
                    # where user could have multiple validators attesting to the same slot
                    f" - [{', '.join(validators)}]"
                )

            print()
            print("*" * 80)
            print()

            print(
                "Searching for sync committee membership (This committee and next, "
                f"+{self.SECONDS_PER_SLOT * self.SLOTS_PER_EPOCH * self.EPOCHS_PER_COMMITTEE / 3600}H)")

            cur_committee_start_epoch = epoch // Duties.EPOCHS_PER_COMMITTEE * 256
            next_committee_start_epoch = cur_committee_start_epoch + 256

            cur_epoch_sync_duties = self.api_post(
                f"validator/duties/sync/{cur_committee_start_epoch}",
                json.dumps(self.validators_indices)
            )["data"]

            if cur_epoch_sync_duties:
                committee_end = datetime.fromtimestamp(
                    self.GENESIS_TIMESTAMP +
                    next_committee_start_epoch *
                    self.SLOTS_PER_EPOCH *
                    self.SECONDS_PER_SLOT
                )
                print("Validator currently in committee")
                print(f"Ending at {committee_end.isoformat()}")

            next_epoch_sync_duties = self.api_post(
                f"validator/duties/sync/{next_committee_start_epoch}",
                json.dumps(self.validators_indices)
            )["data"]

            if next_epoch_sync_duties:
                committee_start = datetime.fromtimestamp(
                    self.GENESIS_TIMESTAMP +
                    next_committee_start_epoch *
                    self.SLOTS_PER_EPOCH *
                    self.SECONDS_PER_SLOT
                )
                print("Validator joining upcoming sync committee")
                print(f"Starts at {committee_start.isoformat()}")

            print()
            print("*" * 80)
            print()

        attestation_duties = self.post_and_merge_data(
            "validator/duties/attester",
            head_slot)

        # Also insert (still unknown) attestation duties at epoch after next,
        # assuming worst case of having to attest at its first slot
        first_slot_epoch_p2 = (epoch + 2) * self.SLOTS_PER_EPOCH
        attestation_duties[first_slot_epoch_p2] = []

        print(f"Calculating attestation slots and gaps for validators:")
        print(f"  {self.validators_indices}")

        print("\nUpcoming voting slots and gaps")
        print("(Gap in seconds)")
        print("(slot/epoch - time range - validators)")
        print("-" * 80)

        prev_end_time = datetime.now()
        longest_gap = timedelta(seconds=0)
        gap_time_range = (None, None)

        for slot, validators in attestation_duties.items():
            slot_start = datetime.fromtimestamp(
                self.GENESIS_TIMESTAMP + slot * self.SECONDS_PER_SLOT)
            slot_end = slot_start + timedelta(seconds=self.SECONDS_PER_SLOT)

            gap = slot_start - prev_end_time
            print(
                f"Idle Gap - {math.floor((slot_start - prev_end_time).total_seconds())} seconds")

            if validators:
                print(
                    f"  Active {slot}/{slot // self.SLOTS_PER_EPOCH}"
                    f" - {slot_start.strftime('%H:%M:%S')} until {slot_end.strftime('%H:%M:%S')}"
                    f" - [{', '.join(validators)}]"
                )
            else:
                # first slot of future epoch (cur_epoch+2) with
                # unknown validator placement
                assert slot % self.SLOTS_PER_EPOCH == 0

            if gap > longest_gap:
                longest_gap = gap
                gap_time_range = (prev_end_time, slot_start)

            prev_end_time = slot_end

        print("\nLongest gap (first):")
        print("-" * 80)
        print(
            f"{longest_gap.total_seconds()} seconds"
            f" ({int(longest_gap.total_seconds()) // self.SECONDS_PER_SLOT} slots),"
            f" from {gap_time_range[0].strftime('%H:%M:%S')}"
            f" until {gap_time_range[1].strftime('%H:%M:%S')}"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Show upcoming validator duties (attestations/block proposals/sync committee memberships)."
    )
    parser.add_argument(
        "indices",
        metavar="index",
        type=int,
        nargs="+",
        help="validator indices")
    parser.add_argument(
        "-u",
        "--api-url",
        dest="api_url",
        type=str,
        default="http://127.0.0.1:5052/eth/v1/",
        help="Consensus/beacon node http api url")
    parser.add_argument(
        "-a",
        "--attestations-only",
        action='store_true',
        dest="attestations_only",
        help="Only search for attestations. "
        "Default run can be time consuming and "
        "when searching for the perfect gap seconds sometimes matter.")

    args = parser.parse_args()

    duties = Duties(args.indices, args.api_url, args.attestations_only)
    duties.main()

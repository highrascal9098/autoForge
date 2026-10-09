import os
import json
import sqlite3
import argparse
import logging
from outreach.agent import OutreachAgent
from outreach.generator import load_profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("outreach.main")

def main():
    parser = argparse.ArgumentParser(description="AutoForge AI Outreach Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # draft
    parser_draft = subparsers.add_parser("draft", help="Draft outreach for discovered jobs")
    parser_draft.add_argument("--limit", type=int, default=5, help="Number of jobs to draft for")

    # list-pending
    subparsers.add_parser("list-pending", help="List drafted outreach pending approval")

    # approve
    parser_parser = subparsers.add_parser("approve", help="Approve a draft outreach")
    parser_parser.add_argument("--id", type=int, required=True, help="Outreach ID to approve")

    # send-approved
    parser_send = subparsers.add_parser("send-approved", help="Send approved outreach messages")
    parser_send.add_argument("--id", type=int, help="Specific outreach ID to send")

    # status
    subparsers.add_parser("status", help="Show outreach statistics and statuses")

    args = parser.parse_args()
    agent = OutreachAgent()
    profile = load_profile()

    if args.command == "draft":
        agent.create_drafts(limit=args.limit)

    elif args.command == "list-pending":
        pending = agent.tracker.get_pending_approval()
        print("\n--- Drafted Outreach Pending Approval ---")
        for row in pending:
            # Note: Company/Title might need joining or fetching from jobs table via tracker/agent
            print(f"ID: {row['id']} | Email: {row['recruiter_email']} | Subject: {row['email_subject']}")
        print(f"Total pending: {len(pending)}\n")

    elif args.command == "approve":
        success = agent.approve_draft(args.id)
        if success:
            logger.info(f"Outreach ID {args.id} approved successfully.")
        else:
            logger.error(f"Failed to approve outreach ID {args.id} (must be in 'drafted' status).")

    elif args.command == "send-approved":
        if args.id:
            # Need to implement specific ID send in agent/sender if needed
            logger.warning("Sending specific ID not yet implemented in agent.")
        else:
            sent = agent.send_approved(limit=10)
            logger.info(f"Sent {sent} approved outreach messages.")

    elif args.command == "status":
        stats = agent.tracker.get_stats()
        print("\n--- Outreach Statistics ---")
        for stat in stats:
            print(f"{stat['status'].upper()}: {stat['count']}")
        print()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

"""AWS Lambda handler for Sandstone decay engine."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def handler(event, context):
    try:
        from core.decay import run_decay_update, archive_cold_nodes
        updated_count = run_decay_update()
        archived_count = archive_cold_nodes()
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'complete',
                'nodes_updated': updated_count,
                'nodes_archived': archived_count,
            })
        }
        print(f"Decay complete: {updated_count} updated, {archived_count} archived")
        return result
    except Exception as e:
        print(f"Decay error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'status': 'error', 'error': str(e)})}

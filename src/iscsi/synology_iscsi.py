# src/iscsi/synology_iscsi.py - Synology iSCSI/SAN Manager API utilities
#
# Implements the SYNO.Core.ISCSI.LUN API for managing iSCSI LUNs.
# API is undocumented by Synology but reverse-engineered from:
# https://github.com/kwent/syno/blob/master/definitions/6.x/SYNO.Core.ISCSI.lib

import requests
from typing import Dict, List, Any, Optional


class SynologyISCSI:
    """Handles Synology iSCSI/SAN Manager API operations."""

    def __init__(self, base_url: str, session_id: str):
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id
        self.api_url = f"{self.base_url}/webapi/entry.cgi"

    def _make_request(self, api: str, version: str, method: str, **params) -> Dict[str, Any]:
        """Make a request to Synology API."""
        request_params = {
            'api': api,
            'version': version,
            'method': method,
            '_sid': self.session_id,
            **params
        }

        response = requests.get(self.api_url, params=request_params, verify=False)
        response.raise_for_status()

        data = response.json()
        if not data.get('success'):
            error_code = data.get('error', {}).get('code', 'unknown')
            error_info = data.get('error', {})

            error_message = f"Synology iSCSI API error: {error_code}"

            # Include detailed error information if available
            if 'errors' in error_info and error_info['errors']:
                detailed_errors = []
                for err in error_info['errors']:
                    err_detail = f"Code {err.get('code', 'unknown')}"
                    if 'path' in err:
                        err_detail += f" for path: {err['path']}"
                    detailed_errors.append(err_detail)
                error_message += f" - Details: {'; '.join(detailed_errors)}"

            raise Exception(error_message)

        return data.get('data', {})

    def list_luns(self) -> List[Dict[str, Any]]:
        """
        List all iSCSI LUNs.

        Returns:
            List of LUN dictionaries with uuid, name, size, status, etc.
        """
        data = self._make_request('SYNO.Core.ISCSI.LUN', '1', 'list')
        luns = data.get('luns', [])

        result = []
        for lun in luns:
            result.append({
                'uuid': lun.get('uuid'),
                'name': lun.get('name'),
                'size': lun.get('size', 0),
                'size_gb': round(lun.get('size', 0) / (1024 ** 3), 2),
                'status': lun.get('status'),
                'used_size': lun.get('used_size', 0),
                'used_size_gb': round(lun.get('used_size', 0) / (1024 ** 3), 2),
                'location': lun.get('location'),
                'is_mapped': lun.get('is_mapped', False),
                'is_online': lun.get('is_online', False),
                'type': lun.get('type'),
                'thin_provisioning': lun.get('thin_provisioning', False),
            })

        return result

    def get_lun(self, uuid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific LUN.

        Args:
            uuid: The UUID of the LUN to retrieve.

        Returns:
            LUN details dictionary.
        """
        data = self._make_request('SYNO.Core.ISCSI.LUN', '1', 'get', uuid=uuid)
        lun = data.get('lun', {})

        return {
            'uuid': lun.get('uuid'),
            'name': lun.get('name'),
            'size': lun.get('size', 0),
            'size_gb': round(lun.get('size', 0) / (1024 ** 3), 2),
            'status': lun.get('status'),
            'used_size': lun.get('used_size', 0),
            'used_size_gb': round(lun.get('used_size', 0) / (1024 ** 3), 2),
            'location': lun.get('location'),
            'is_mapped': lun.get('is_mapped', False),
            'is_online': lun.get('is_online', False),
            'type': lun.get('type'),
            'thin_provisioning': lun.get('thin_provisioning', False),
            'targets': lun.get('targets', []),
            'can_do_snapshot': lun.get('can_do_snapshot', False),
            'is_action_locked': lun.get('is_action_locked', False),
        }

    def delete_lun(self, uuid: str) -> Dict[str, Any]:
        """
        Delete an iSCSI LUN.

        WARNING: This permanently deletes the LUN and all data on it.

        Args:
            uuid: The UUID of the LUN to delete.

        Returns:
            Result of the delete operation.
        """
        # First check if LUN exists and is unmapped
        try:
            lun_info = self.get_lun(uuid)
            if lun_info.get('is_mapped'):
                raise Exception(
                    f"LUN {uuid} is still mapped to targets. "
                    f"Unmap it first before deletion."
                )
        except Exception as e:
            if "iSCSI API error" in str(e):
                raise Exception(f"LUN {uuid} not found or inaccessible: {e}")
            raise

        # Perform deletion
        data = self._make_request('SYNO.Core.ISCSI.LUN', '1', 'delete', uuid=uuid)

        return {
            'success': True,
            'uuid': uuid,
            'message': f"LUN {uuid} deleted successfully"
        }

    def list_targets(self) -> List[Dict[str, Any]]:
        """
        List all iSCSI targets.

        Returns:
            List of target dictionaries.
        """
        data = self._make_request('SYNO.Core.ISCSI.Target', '1', 'list')
        targets = data.get('targets', [])

        result = []
        for target in targets:
            result.append({
                'target_id': target.get('target_id'),
                'name': target.get('name'),
                'iqn': target.get('iqn'),
                'status': target.get('status'),
                'mapped_luns': target.get('mapped_luns', []),
                'connected_sessions': target.get('connected_sessions', 0),
            })

        return result

    def unmap_lun(self, lun_uuid: str, target_id: str) -> Dict[str, Any]:
        """
        Unmap a LUN from an iSCSI target.

        Args:
            lun_uuid: The UUID of the LUN.
            target_id: The target ID to unmap from.

        Returns:
            Result of the unmap operation.
        """
        data = self._make_request(
            'SYNO.Core.ISCSI.LUN', '1', 'unmap_target',
            uuid=lun_uuid,
            target_id=target_id
        )

        return {
            'success': True,
            'lun_uuid': lun_uuid,
            'target_id': target_id,
            'message': f"LUN {lun_uuid} unmapped from target {target_id}"
        }

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import NetworkLink
from inventory.models import Host

class TopologyViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['get'])
    def graph(self, request):
        """
        Returns the network topology as a graph (nodes and links).
        """
        nodes = []
        links = []
        
        # Add all hosts as nodes
        hosts = Host.objects.all()
        for host in hosts:
            nodes.append({
                'id': host.hostname,
                'display_name': host.display_name,
                'ip': host.ip_address,
                'status': host.status,
                'group': host.group.name if host.group else 'Default',
                'type': 'host',
                'mac_address': host.mac_address,
                'vendor': host.vendor
            })
            
            # Add hierarchy link if parent exists
            if host.parent:
                links.append({
                    'source': host.parent.hostname,
                    'target': host.hostname,
                    'type': 'hierarchy'
                })
            
        # Add links
        network_links = NetworkLink.objects.all()
        for link in network_links:
            target_id = link.target.hostname if link.target else (link.target_ip or link.target_mac or f"unknown-{link.id}")
            
            # If target node doesn't exist (e.g. unmanaged device), add it strictly for the graph
            if not any(n['id'] == target_id for n in nodes):
                 nodes.append({
                    'id': target_id,
                    'type': 'unknown',
                    'status': 'unknown'
                 })

            links.append({
                'source': link.source.hostname,
                'target': target_id,
                'protocol': link.protocol,
                'type': link.link_type
            })
            
        return Response({
            'nodes': nodes,
            'links': links
        })

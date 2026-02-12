"""Advanced API interaction tools for REST, GraphQL, and webhook handling."""

import time
import json
import requests
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import logging

from ..core.tool_base import BaseTool, AsyncBaseTool, ToolResult, ToolStatus, ToolValidationError
from ..core.tool_registry import tool_decorator
from ..utils.advanced_rate_limiter import get_global_rate_limiter, RateLimitConfig, RateLimitAlgorithm
from ..utils.error_recovery import ErrorRecovery, RetryConfig, CircuitBreakerConfig

logger = logging.getLogger(__name__)


@dataclass
class APITestCase:
    """API test case definition."""
    
    name: str
    method: str
    endpoint: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    expected_fields: List[str] = field(default_factory=list)
    timeout: float = 30.0


@dataclass
class APIResponse:
    """Standardized API response."""
    
    status_code: int
    headers: Dict[str, str]
    data: Any
    response_time: float
    url: str
    method: str
    success: bool
    error: Optional[str] = None


@tool_decorator(name="rest_client", category="api", tags=["rest", "http", "client"])
class RESTClient(BaseTool):
    """Advanced REST API client with authentication, retries, and rate limiting."""
    
    def __init__(self, base_url: str = "", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set up error recovery
        self.error_recovery = ErrorRecovery(
            retry_config=RetryConfig(max_attempts=3),
            circuit_config=CircuitBreakerConfig(failure_threshold=5)
        )
        
        # Set up rate limiting
        rate_limiter = get_global_rate_limiter()
        rate_config = RateLimitConfig(
            max_requests=100,
            time_window=60.0,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET
        )
        rate_limiter.add_limiter("rest_client", rate_config)
        
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate REST request parameters."""
        method = kwargs.get('method', 'GET').upper()
        if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            raise ToolValidationError(f"Invalid HTTP method: {method}", self.tool_id)
            
        endpoint = kwargs.get('endpoint')
        if not endpoint:
            raise ToolValidationError("endpoint is required", self.tool_id)
            
        return {
            'method': method,
            'endpoint': endpoint,
            'headers': kwargs.get('headers', {}),
            'params': kwargs.get('params', {}),
            'data': kwargs.get('data'),
            'json_data': kwargs.get('json_data'),
            'auth': kwargs.get('auth'),
            'timeout': kwargs.get('timeout', 30.0),
            'follow_redirects': kwargs.get('follow_redirects', True),
            'verify_ssl': kwargs.get('verify_ssl', True)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute REST API request."""
        method = kwargs['method']
        endpoint = kwargs['endpoint']
        headers = kwargs['headers']
        params = kwargs['params']
        data = kwargs['data']
        json_data = kwargs['json_data']
        auth = kwargs['auth']
        timeout = kwargs['timeout']
        follow_redirects = kwargs['follow_redirects']
        verify_ssl = kwargs['verify_ssl']
        
        try:
            # Build full URL
            if endpoint.startswith(('http://', 'https://')):
                url = endpoint
            else:
                url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
                
            # Set up authentication
            if auth:
                if auth.get('type') == 'bearer':
                    headers['Authorization'] = f"Bearer {auth['token']}"
                elif auth.get('type') == 'basic':
                    self.session.auth = (auth['username'], auth['password'])
                elif auth.get('type') == 'api_key':
                    if auth.get('location') == 'header':
                        headers[auth['key']] = auth['value']
                    else:
                        params[auth['key']] = auth['value']
                        
            # Prepare request arguments
            request_kwargs = {
                'url': url,
                'headers': headers,
                'params': params,
                'timeout': timeout,
                'allow_redirects': follow_redirects,
                'verify': verify_ssl
            }
            
            if json_data:
                request_kwargs['json'] = json_data
            elif data:
                request_kwargs['data'] = data
                
            # Execute with error recovery
            def make_request():
                # Rate limiting check
                rate_limiter = get_global_rate_limiter()
                if not rate_limiter.check_limits("rest_client"):
                    wait_time = rate_limiter.wait_time("rest_client")
                    time.sleep(wait_time)
                    
                start_time = time.time()
                response = self.session.request(method, **request_kwargs)
                response_time = time.time() - start_time
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text
                    
                api_response = APIResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    data=response_data,
                    response_time=response_time,
                    url=response.url,
                    method=method,
                    success=200 <= response.status_code < 400
                )
                
                # Raise for HTTP errors to trigger retry if needed
                if not api_response.success:
                    api_response.error = f"HTTP {response.status_code}: {response.reason}"
                    if response.status_code >= 500:  # Only retry server errors
                        response.raise_for_status()
                        
                return api_response
                
            api_response = self.error_recovery.execute(make_request)
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS if api_response.success else ToolStatus.FAILED,
                data={
                    'response': {
                        'status_code': api_response.status_code,
                        'headers': api_response.headers,
                        'data': api_response.data,
                        'response_time': api_response.response_time,
                        'url': api_response.url,
                        'method': api_response.method,
                        'success': api_response.success
                    },
                    'request': {
                        'method': method,
                        'url': url,
                        'headers': headers,
                        'params': params
                    }
                },
                error=api_response.error
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )


@tool_decorator(name="graphql_client", category="api", tags=["graphql", "query", "client"])
class GraphQLClient(BaseTool):
    """GraphQL client with query validation and introspection."""
    
    def __init__(self, endpoint: str = "", **kwargs):
        super().__init__(**kwargs)
        self.endpoint = endpoint
        self.session = requests.Session()
        
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate GraphQL request parameters."""
        query = kwargs.get('query')
        endpoint = kwargs.get('endpoint') or self.endpoint
        
        if not query:
            raise ToolValidationError("GraphQL query is required", self.tool_id)
            
        if not endpoint:
            raise ToolValidationError("GraphQL endpoint is required", self.tool_id)
            
        return {
            'query': query,
            'variables': kwargs.get('variables', {}),
            'endpoint': endpoint,
            'headers': kwargs.get('headers', {}),
            'auth': kwargs.get('auth'),
            'timeout': kwargs.get('timeout', 30.0)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute GraphQL query."""
        query = kwargs['query']
        variables = kwargs['variables']
        endpoint = kwargs['endpoint']
        headers = kwargs['headers']
        auth = kwargs['auth']
        timeout = kwargs['timeout']
        
        try:
            # Set up headers
            headers = headers.copy()
            headers.setdefault('Content-Type', 'application/json')
            
            # Set up authentication
            if auth:
                if auth.get('type') == 'bearer':
                    headers['Authorization'] = f"Bearer {auth['token']}"
                elif auth.get('type') == 'api_key':
                    headers[auth['key']] = auth['value']
                    
            # Prepare GraphQL request
            payload = {
                'query': query,
                'variables': variables
            }
            
            start_time = time.time()
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response_time = time.time() - start_time
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check for GraphQL errors
            graphql_errors = response_data.get('errors', [])
            has_errors = bool(graphql_errors)
            
            result_data = {
                'data': response_data.get('data'),
                'errors': graphql_errors,
                'extensions': response_data.get('extensions'),
                'response_time': response_time,
                'status_code': response.status_code,
                'has_errors': has_errors,
                'query': query,
                'variables': variables
            }
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS if not has_errors else ToolStatus.FAILED,
                data=result_data,
                error='; '.join(err.get('message', '') for err in graphql_errors) if has_errors else None
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def introspect(self, endpoint: Optional[str] = None) -> ToolResult:
        """Perform GraphQL schema introspection."""
        endpoint = endpoint or self.endpoint
        
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                    description
                    fields {
                        name
                        type {
                            name
                            kind
                        }
                        args {
                            name
                            type {
                                name
                                kind
                            }
                        }
                    }
                }
                queryType {
                    name
                }
                mutationType {
                    name
                }
                subscriptionType {
                    name
                }
            }
        }
        """
        
        return self.execute(
            query=introspection_query,
            endpoint=endpoint
        )


@tool_decorator(name="webhook_receiver", category="api", tags=["webhook", "server", "callback"])
class WebhookReceiver(BaseTool):
    """Webhook receiver and handler."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.received_webhooks = []
        
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate webhook parameters."""
        action = kwargs.get('action', 'start')
        
        if action not in ['start', 'stop', 'list', 'clear']:
            raise ToolValidationError(f"Invalid action: {action}", self.tool_id)
            
        return {
            'action': action,
            'port': kwargs.get('port', 8080),
            'path': kwargs.get('path', '/webhook'),
            'timeout': kwargs.get('timeout', 60.0),
            'max_webhooks': kwargs.get('max_webhooks', 100)
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute webhook operation."""
        action = kwargs['action']
        port = kwargs['port']
        path = kwargs['path']
        timeout = kwargs['timeout']
        max_webhooks = kwargs['max_webhooks']
        
        try:
            if action == 'start':
                return self._start_webhook_server(port, path, timeout, max_webhooks)
            elif action == 'stop':
                return self._stop_webhook_server()
            elif action == 'list':
                return self._list_webhooks()
            elif action == 'clear':
                return self._clear_webhooks()
                
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _start_webhook_server(self, port: int, path: str, timeout: float, max_webhooks: int) -> ToolResult:
        """Start webhook server (simplified implementation)."""
        # This is a simplified placeholder - in real implementation, would use Flask/FastAPI
        return ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.SUCCESS,
            data={
                'message': f'Webhook server would start on port {port} at path {path}',
                'endpoint': f'http://localhost:{port}{path}',
                'timeout': timeout,
                'status': 'simulated'
            }
        )
        
    def _stop_webhook_server(self) -> ToolResult:
        """Stop webhook server."""
        return ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.SUCCESS,
            data={
                'message': 'Webhook server stopped',
                'status': 'simulated'
            }
        )
        
    def _list_webhooks(self) -> ToolResult:
        """List received webhooks."""
        return ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.SUCCESS,
            data={
                'webhooks': self.received_webhooks,
                'count': len(self.received_webhooks)
            }
        )
        
    def _clear_webhooks(self) -> ToolResult:
        """Clear webhook history."""
        count = len(self.received_webhooks)
        self.received_webhooks.clear()
        
        return ToolResult(
            tool_id=self.tool_id,
            status=ToolStatus.SUCCESS,
            data={
                'message': f'Cleared {count} webhooks',
                'cleared_count': count
            }
        )


@tool_decorator(name="api_tester", category="api", tags=["testing", "validation", "automation"])
class APITester(BaseTool):
    """Comprehensive API testing and validation tool."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rest_client = RESTClient()
        
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate API testing parameters."""
        test_cases = kwargs.get('test_cases')
        if not test_cases:
            raise ToolValidationError("test_cases are required", self.tool_id)
            
        if not isinstance(test_cases, list):
            raise ToolValidationError("test_cases must be a list", self.tool_id)
            
        return {
            'test_cases': test_cases,
            'base_url': kwargs.get('base_url', ''),
            'parallel': kwargs.get('parallel', False),
            'stop_on_failure': kwargs.get('stop_on_failure', False),
            'auth': kwargs.get('auth'),
            'global_headers': kwargs.get('global_headers', {})
        }
        
    def execute(self, **kwargs) -> ToolResult:
        """Execute API test suite."""
        test_cases = kwargs['test_cases']
        base_url = kwargs['base_url']
        parallel = kwargs['parallel']
        stop_on_failure = kwargs['stop_on_failure']
        auth = kwargs['auth']
        global_headers = kwargs['global_headers']
        
        try:
            # Parse test cases
            parsed_cases = []
            for i, case_data in enumerate(test_cases):
                if isinstance(case_data, dict):
                    test_case = APITestCase(
                        name=case_data.get('name', f'Test {i+1}'),
                        method=case_data.get('method', 'GET'),
                        endpoint=case_data.get('endpoint', ''),
                        headers=case_data.get('headers', {}),
                        params=case_data.get('params', {}),
                        data=case_data.get('data'),
                        expected_status=case_data.get('expected_status', 200),
                        expected_fields=case_data.get('expected_fields', []),
                        timeout=case_data.get('timeout', 30.0)
                    )
                    parsed_cases.append(test_case)
                    
            # Execute tests
            if parallel:
                results = self._execute_parallel(parsed_cases, base_url, auth, global_headers)
            else:
                results = self._execute_sequential(parsed_cases, base_url, auth, global_headers, stop_on_failure)
                
            # Analyze results
            analysis = self._analyze_results(results)
            
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.SUCCESS if analysis['overall_success'] else ToolStatus.FAILED,
                data={
                    'test_results': results,
                    'analysis': analysis,
                    'total_tests': len(parsed_cases)
                }
            )
            
        except Exception as e:
            return ToolResult(
                tool_id=self.tool_id,
                status=ToolStatus.FAILED,
                error=str(e)
            )
            
    def _execute_sequential(self, test_cases: List[APITestCase], base_url: str, auth: Optional[Dict], global_headers: Dict, stop_on_failure: bool) -> List[Dict[str, Any]]:
        """Execute test cases sequentially."""
        results = []
        
        for test_case in test_cases:
            start_time = time.time()
            
            try:
                # Merge headers
                headers = global_headers.copy()
                headers.update(test_case.headers)
                
                # Build URL
                if test_case.endpoint.startswith(('http://', 'https://')):
                    url = test_case.endpoint
                else:
                    url = urljoin(base_url + '/', test_case.endpoint.lstrip('/'))
                    
                # Execute request
                response = requests.request(
                    method=test_case.method,
                    url=url,
                    headers=headers,
                    params=test_case.params,
                    json=test_case.data,
                    timeout=test_case.timeout,
                    auth=(auth['username'], auth['password']) if auth and auth.get('type') == 'basic' else None
                )
                
                # Parse response
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text
                    
                # Validate response
                validations = self._validate_response(response, response_data, test_case)
                
                test_result = {
                    'name': test_case.name,
                    'method': test_case.method,
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': time.time() - start_time,
                    'success': validations['overall_success'],
                    'validations': validations,
                    'response_data': response_data,
                    'error': None
                }
                
            except Exception as e:
                test_result = {
                    'name': test_case.name,
                    'method': test_case.method,
                    'url': url if 'url' in locals() else 'N/A',
                    'status_code': None,
                    'response_time': time.time() - start_time,
                    'success': False,
                    'validations': {'overall_success': False},
                    'response_data': None,
                    'error': str(e)
                }
                
            results.append(test_result)
            
            # Stop on failure if requested
            if stop_on_failure and not test_result['success']:
                break
                
        return results
        
    def _execute_parallel(self, test_cases: List[APITestCase], base_url: str, auth: Optional[Dict], global_headers: Dict) -> List[Dict[str, Any]]:
        """Execute test cases in parallel."""
        import concurrent.futures
        
        def execute_single_test(test_case):
            return self._execute_sequential([test_case], base_url, auth, global_headers, False)[0]
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_test = {executor.submit(execute_single_test, tc): tc for tc in test_cases}
            results = []
            
            for future in concurrent.futures.as_completed(future_to_test):
                result = future.result()
                results.append(result)
                
        return results
        
    def _validate_response(self, response: requests.Response, response_data: Any, test_case: APITestCase) -> Dict[str, Any]:
        """Validate API response against test case expectations."""
        validations = {
            'status_code_match': response.status_code == test_case.expected_status,
            'response_time_ok': True,  # Could add response time validation
            'expected_fields_present': True,
            'field_validations': {}
        }
        
        # Validate expected fields
        if test_case.expected_fields and isinstance(response_data, dict):
            for field in test_case.expected_fields:
                field_present = field in response_data
                validations['field_validations'][field] = field_present
                if not field_present:
                    validations['expected_fields_present'] = False
                    
        # Overall success
        validations['overall_success'] = all([
            validations['status_code_match'],
            validations['response_time_ok'],
            validations['expected_fields_present']
        ])
        
        return validations
        
    def _analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test results."""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - passed_tests
        
        total_time = sum(r['response_time'] for r in results)
        avg_response_time = total_time / total_tests if total_tests > 0 else 0
        
        status_codes = {}
        for result in results:
            status = result.get('status_code')
            if status:
                status_codes[status] = status_codes.get(status, 0) + 1
                
        return {
            'overall_success': failed_tests == 0,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'pass_rate': (passed_tests / total_tests) if total_tests > 0 else 0,
            'total_time': total_time,
            'average_response_time': avg_response_time,
            'status_code_distribution': status_codes,
            'failed_test_names': [r['name'] for r in results if not r['success']]
        }
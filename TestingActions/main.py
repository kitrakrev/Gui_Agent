"""
Main entry point for BrowserGym Actions Runner
Uses bgym_utils functions to execute browser automation actions.
"""

import argparse
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

# Import bgym_utils functions
from utils.bgym_utils.functions import *
from utils.bgym_utils.utils import get_elem_by_bid
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# Global variables for bgym_utils
page = None
send_message_to_user = None
report_infeasible_instructions = None
demo_mode = "off"
retry_with_force = False


@dataclass
class Action:
    """Represents a single BrowserGym action."""
    action_type: str
    parameters: List[str]
    line_number: int


class BrowserGymRunner:
    """Main class for running BrowserGym actions using bgym_utils."""
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        Initialize the BrowserGymRunner.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: Type of browser to use (chromium, firefox, webkit)
        """
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Action handlers mapping
        self.action_handlers = {
            'navigate': self._handle_navigate,
            'goto': self._handle_goto,
            'click': self._handle_click,
            'dblclick': self._handle_dblclick,
            'hover': self._handle_hover,
            'fill': self._handle_fill,
            'type': self._handle_fill,  # Alias for fill
            'clear': self._handle_clear,
            'check': self._handle_check,
            'uncheck': self._handle_uncheck,
            'select_option': self._handle_select_option,
            'select': self._handle_select_option,  # Alias for select_option
            'wait': self._handle_wait,
            'noop': self._handle_noop,
            'scroll': self._handle_scroll,
            'scroll_at': self._handle_scroll_at,
            'screenshot': self._handle_screenshot,
            'mouse_move': self._handle_mouse_move,
            'mouse_click': self._handle_mouse_click,
            'mouse_dblclick': self._handle_mouse_dblclick,
            'mouse_drag_and_drop': self._handle_mouse_drag_and_drop,
            'drag_and_drop': self._handle_drag_and_drop,
            'keyboard_press': self._handle_keyboard_press,
            'keyboard_type': self._handle_keyboard_type,
            'keyboard_down': self._handle_keyboard_down,
            'keyboard_up': self._handle_keyboard_up,
            'focus': self._handle_focus,
            'go_back': self._handle_go_back,
            'go_forward': self._handle_go_forward,
            'new_tab': self._handle_new_tab,
            'tab_close': self._handle_tab_close,
            'tab_focus': self._handle_tab_focus,
            'upload_file': self._handle_upload_file,
            'mouse_upload_file': self._handle_mouse_upload_file,
            'send_msg': self._handle_send_msg,
            'report_infeasible': self._handle_report_infeasible,
            'get_bids': self._handle_get_bids,  # New action to get available BIDs
            'find_element': self._handle_find_element, # New action to find elements by properties
            'test_bid': self._handle_test_bid, # New action to test BID.js injection
            'direct_fill': self._handle_direct_fill, # New action for direct Playwright fill
            'direct_click': self._handle_direct_click, # New action for direct Playwright click
            'direct_press': self._handle_direct_press, # New action for direct Playwright press
        }
    
    def setup_browser(self):
        """Set up the browser using Playwright."""
        try:
            self.playwright = sync_playwright().start()
            
            if self.browser_type.lower() == "chromium":
                self.browser = self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type.lower() == "firefox":
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type.lower() == "webkit":
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = self.context.new_page()
            
            # Inject BID.js script into all pages
            self.page.add_init_script("""
                // BID.js - BrowserGym Element ID Injection
                (function() {
                    if (window.BID_INJECTED) return;
                    window.BID_INJECTED = true;
                    
                    let bidCounter = 0;
                    const bidPrefix = 'bgym_';
                    
                    function generateBID() {
                        return bidPrefix + (bidCounter++).toString(36);
                    }
                    
                    function addBIDToElement(element) {
                        if (!element || element.hasAttribute('data-testid') || element.hasAttribute('data-bgym-id')) {
                            return;
                        }
                        
                        // Skip certain elements
                        if (element.tagName === 'SCRIPT' || element.tagName === 'STYLE' || element.tagName === 'META') {
                            return;
                        }
                        
                        // Add BID to element
                        const bid = generateBID();
                        element.setAttribute('data-testid', bid);
                        element.setAttribute('data-bgym-id', bid);
                    }
                    
                    function processElement(element) {
                        addBIDToElement(element);
                        
                        // Process child elements
                        const children = element.children;
                        for (let i = 0; i < children.length; i++) {
                            processElement(children[i]);
                        }
                    }
                    
                    function processNewElements() {
                        const observer = new MutationObserver(function(mutations) {
                            mutations.forEach(function(mutation) {
                                mutation.addedNodes.forEach(function(node) {
                                    if (node.nodeType === Node.ELEMENT_NODE) {
                                        processElement(node);
                                    }
                                });
                            });
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                    }
                    
                    // Process existing elements
                    if (document.body) {
                        processElement(document.body);
                    } else {
                        document.addEventListener('DOMContentLoaded', function() {
                            processElement(document.body);
                        });
                    }
                    
                    // Process new elements
                    if (document.body) {
                        processNewElements();
                    } else {
                        document.addEventListener('DOMContentLoaded', function() {
                            processNewElements();
                        });
                    }
                    
                    // Make BID functions globally available
                    window.BrowserGym = window.BrowserGym || {};
                    window.BrowserGym.generateBID = generateBID;
                    window.BrowserGym.addBIDToElement = addBIDToElement;
                    window.BrowserGym.processElement = processElement;
                    
                    console.log('BID.js injected successfully');
                })();
            """)
            
            # Set global variables directly in the bgym_utils module
            import utils.bgym_utils.functions as bgym_functions
            bgym_functions.page = self.page
            bgym_functions.send_message_to_user = self._default_send_message
            bgym_functions.report_infeasible_instructions = self._default_report_infeasible
            bgym_functions.demo_mode = "off"
            bgym_functions.retry_with_force = False
            
            # Also set our local globals for consistency
            global page, send_message_to_user, report_infeasible_instructions, demo_mode, retry_with_force
            page = self.page
            send_message_to_user = self._default_send_message
            report_infeasible_instructions = self._default_report_infeasible
            demo_mode = "off"
            retry_with_force = False
            
            logger.info(f"Successfully initialized {self.browser_type} browser with BID.js injection")
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            raise
    
    def parse_actions_file(self, file_path: str) -> List[Action]:
        """
        Parse a BrowserGym actions file.
        
        Args:
            file_path: Path to the actions file
            
        Returns:
            List of parsed Action objects
        """
        actions = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Actions file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse action line: action_type|param1|param2|...
                parts = line.split('|')
                if len(parts) < 1:
                    logger.warning(f"Invalid action format at line {line_num}: {line}")
                    continue
                
                action_type = parts[0].strip()
                parameters = [p.strip() for p in parts[1:]]
                
                action = Action(
                    action_type=action_type,
                    parameters=parameters,
                    line_number=line_num
                )
                actions.append(action)
        
        logger.info(f"Parsed {len(actions)} actions from {file_path}")
        return actions
    
    def run_actions(self, actions: List[Action]) -> Dict[str, Any]:
        """
        Execute a list of actions.
        
        Args:
            actions: List of Action objects to execute
            
        Returns:
            Dictionary containing execution results
        """
        # Ensure browser is set up before executing any actions
        if not self.page:
            self.setup_browser()
        
        # Double-check that global variables are set
        global page, send_message_to_user, report_infeasible_instructions
        if page is None:
            page = self.page
        if send_message_to_user is None:
            send_message_to_user = self._default_send_message
        if report_infeasible_instructions is None:
            report_infeasible_instructions = self._default_report_infeasible
        
        results = {
            'total_actions': len(actions),
            'successful_actions': 0,
            'failed_actions': 0,
            'errors': [],
            'execution_time': 0
        }
        
        start_time = time.time()
        
        for action in actions:
            try:
                logger.info(f"Executing action {action.line_number}: {action.action_type} - {action.parameters}")
                
                if action.action_type in self.action_handlers:
                    self.action_handlers[action.action_type](action.parameters)
                    results['successful_actions'] += 1
                else:
                    logger.warning(f"Unknown action type: {action.action_type}")
                    results['failed_actions'] += 1
                    results['errors'].append({
                        'line': action.line_number,
                        'action': action.action_type,
                        'error': f"Unknown action type: {action.action_type}"
                    })
                    
            except Exception as e:
                logger.error(f"Error executing action {action.line_number}: {e}")
                results['failed_actions'] += 1
                results['errors'].append({
                    'line': action.line_number,
                    'action': action.action_type,
                    'error': str(e)
                })
        
        results['execution_time'] = time.time() - start_time
        logger.info(f"Execution completed: {results['successful_actions']} successful, {results['failed_actions']} failed")
        
        return results
    
    def run_actions_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse and execute actions from a file.
        
        Args:
            file_path: Path to the actions file
            
        Returns:
            Dictionary containing execution results
        """
        actions = self.parse_actions_file(file_path)
        return self.run_actions(actions)
    
    def cleanup(self):
        """Clean up resources."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser resources cleaned up")
    
    # Default handlers for bgym_utils callbacks
    def _default_send_message(self, text: str):
        """Default message handler."""
        logger.info(f"Message: {text}")
    
    def _default_report_infeasible(self, reason: str):
        """Default infeasible instruction handler."""
        logger.warning(f"Infeasible instruction: {reason}")
    
    # Action handlers using bgym_utils functions
    def _handle_navigate(self, params: List[str]):
        """Handle navigate action using goto function."""
        if not params:
            raise ValueError("Navigate action requires a URL")
        url = params[0]
        goto(url)
        logger.info(f"Navigated to: {url}")
    
    def _handle_goto(self, params: List[str]):
        """Handle goto action."""
        if not params:
            raise ValueError("Goto action requires a URL")
        url = params[0]
        goto(url)
        
        # Wait for BID.js to be injected and elements to be processed
        try:
            self.page.wait_for_function("window.BID_INJECTED && document.querySelectorAll('[data-testid]').length > 0", timeout=10000)
            logger.info(f"BID.js elements processed for: {url}")
        except Exception as e:
            logger.warning(f"BID.js processing timeout or error: {e}")
        
        logger.info(f"Goto: {url}")
    
    def _handle_click(self, params: List[str]):
        """Handle click action."""
        if not params:
            raise ValueError("Click action requires a bid")
        bid = params[0]
        button = params[1] if len(params) > 1 else "left"
        click(bid, button=button)
        logger.info(f"Clicked element: {bid}")
    
    def _handle_dblclick(self, params: List[str]):
        """Handle double click action."""
        if not params:
            raise ValueError("Double click action requires a bid")
        bid = params[0]
        button = params[1] if len(params) > 1 else "left"
        dblclick(bid, button=button)
        logger.info(f"Double clicked element: {bid}")
    
    def _handle_hover(self, params: List[str]):
        """Handle hover action."""
        if not params:
            raise ValueError("Hover action requires a bid")
        bid = params[0]
        hover(bid)
        logger.info(f"Hovered over element: {bid}")
    
    def _handle_fill(self, params: List[str]):
        """Handle fill action."""
        if len(params) < 2:
            raise ValueError("Fill action requires bid and value")
        bid, value = params[0], params[1]
        fill(bid, value)
        logger.info(f"Filled element {bid} with: {value}")
    
    def _handle_clear(self, params: List[str]):
        """Handle clear action."""
        if not params:
            raise ValueError("Clear action requires a bid")
        bid = params[0]
        clear(bid)
        logger.info(f"Cleared element: {bid}")
    
    def _handle_check(self, params: List[str]):
        """Handle check action."""
        if not params:
            raise ValueError("Check action requires a bid")
        bid = params[0]
        check(bid)
        logger.info(f"Checked element: {bid}")
    
    def _handle_uncheck(self, params: List[str]):
        """Handle uncheck action."""
        if not params:
            raise ValueError("Uncheck action requires a bid")
        bid = params[0]
        uncheck(bid)
        logger.info(f"Unchecked element: {bid}")
    
    def _handle_select_option(self, params: List[str]):
        """Handle select option action."""
        if len(params) < 2:
            raise ValueError("Select option action requires bid and options")
        bid, options = params[0], params[1]
        # Handle multiple options
        if options.startswith('[') and options.endswith(']'):
            options = options[1:-1].split(',')
        select_option(bid, options)
        logger.info(f"Selected options in {bid}: {options}")
    
    def _handle_wait(self, params: List[str]):
        """Handle wait action."""
        if not params:
            seconds = 1
        else:
            seconds = float(params[0])
        noop(seconds * 1000)  # Convert to milliseconds
        logger.info(f"Waited for {seconds} seconds")
    
    def _handle_noop(self, params: List[str]):
        """Handle noop action."""
        wait_ms = float(params[0]) * 1000 if params else 1000
        noop(wait_ms)
        logger.info(f"Noop for {wait_ms}ms")
    
    def _handle_scroll(self, params: List[str]):
        """Handle scroll action."""
        if len(params) < 2:
            raise ValueError("Scroll action requires delta_x and delta_y")
        delta_x, delta_y = float(params[0]), float(params[1])
        scroll(delta_x, delta_y)
        logger.info(f"Scrolled by ({delta_x}, {delta_y})")
    
    def _handle_scroll_at(self, params: List[str]):
        """Handle scroll at action."""
        if len(params) < 4:
            raise ValueError("Scroll at action requires x, y, dx, dy")
        x, y, dx, dy = int(params[0]), int(params[1]), int(params[2]), int(params[3])
        scroll_at(x, y, dx, dy)
        logger.info(f"Scrolled at ({x}, {y}) by ({dx}, {dy})")
    
    def _handle_screenshot(self, params: List[str]):
        """Handle screenshot action."""
        filename = params[0] if params else f"screenshot_{int(time.time())}.png"
        filepath = self.screenshot_dir / filename
        self.page.screenshot(path=str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
    
    def _handle_mouse_move(self, params: List[str]):
        """Handle mouse move action."""
        if len(params) < 2:
            raise ValueError("Mouse move action requires x and y coordinates")
        x, y = float(params[0]), float(params[1])
        mouse_move(x, y)
        logger.info(f"Moved mouse to ({x}, {y})")
    
    def _handle_mouse_click(self, params: List[str]):
        """Handle mouse click action."""
        if len(params) < 2:
            raise ValueError("Mouse click action requires x and y coordinates")
        x, y = float(params[0]), float(params[1])
        button = params[2] if len(params) > 2 else "left"
        mouse_click(x, y, button=button)
        logger.info(f"Mouse clicked at ({x}, {y}) with {button} button")
    
    def _handle_mouse_dblclick(self, params: List[str]):
        """Handle mouse double click action."""
        if len(params) < 2:
            raise ValueError("Mouse double click action requires x and y coordinates")
        x, y = float(params[0]), float(params[1])
        button = params[2] if len(params) > 2 else "left"
        mouse_dblclick(x, y, button=button)
        logger.info(f"Mouse double clicked at ({x}, {y}) with {button} button")
    
    def _handle_mouse_drag_and_drop(self, params: List[str]):
        """Handle mouse drag and drop action."""
        if len(params) < 4:
            raise ValueError("Mouse drag and drop action requires from_x, from_y, to_x, to_y")
        from_x, from_y, to_x, to_y = float(params[0]), float(params[1]), float(params[2]), float(params[3])
        mouse_drag_and_drop(from_x, from_y, to_x, to_y)
        logger.info(f"Mouse dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})")
    
    def _handle_drag_and_drop(self, params: List[str]):
        """Handle drag and drop action."""
        if len(params) < 2:
            raise ValueError("Drag and drop action requires from_bid and to_bid")
        from_bid, to_bid = params[0], params[1]
        drag_and_drop(from_bid, to_bid)
        logger.info(f"Dragged {from_bid} to {to_bid}")
    
    def _handle_keyboard_press(self, params: List[str]):
        """Handle keyboard press action."""
        if not params:
            raise ValueError("Keyboard press action requires a key")
        key = params[0]
        keyboard_press(key)
        logger.info(f"Pressed key: {key}")
    
    def _handle_keyboard_type(self, params: List[str]):
        """Handle keyboard type action."""
        if not params:
            raise ValueError("Keyboard type action requires text")
        text = params[0]
        keyboard_type(text)
        logger.info(f"Typed: {text}")
    
    def _handle_keyboard_down(self, params: List[str]):
        """Handle keyboard down action."""
        if not params:
            raise ValueError("Keyboard down action requires a key")
        key = params[0]
        keyboard_down(key)
        logger.info(f"Key down: {key}")
    
    def _handle_keyboard_up(self, params: List[str]):
        """Handle keyboard up action."""
        if not params:
            raise ValueError("Keyboard up action requires a key")
        key = params[0]
        keyboard_up(key)
        logger.info(f"Key up: {key}")
    
    def _handle_focus(self, params: List[str]):
        """Handle focus action."""
        if not params:
            raise ValueError("Focus action requires a bid")
        bid = params[0]
        focus(bid)
        logger.info(f"Focused element: {bid}")
    
    def _handle_go_back(self, params: List[str]):
        """Handle go back action."""
        go_back()
        logger.info("Navigated back")
    
    def _handle_go_forward(self, params: List[str]):
        """Handle go forward action."""
        go_forward()
        logger.info("Navigated forward")
    
    def _handle_new_tab(self, params: List[str]):
        """Handle new tab action."""
        new_tab()
        logger.info("Opened new tab")
    
    def _handle_tab_close(self, params: List[str]):
        """Handle tab close action."""
        tab_close()
        logger.info("Closed current tab")
    
    def _handle_tab_focus(self, params: List[str]):
        """Handle tab focus action."""
        if not params:
            raise ValueError("Tab focus action requires an index")
        index = int(params[0])
        tab_focus(index)
        logger.info(f"Focused tab at index: {index}")
    
    def _handle_upload_file(self, params: List[str]):
        """Handle upload file action."""
        if len(params) < 2:
            raise ValueError("Upload file action requires bid and file path")
        bid, file_path = params[0], params[1]
        upload_file(bid, file_path)
        logger.info(f"Uploaded file {file_path} to element {bid}")
    
    def _handle_mouse_upload_file(self, params: List[str]):
        """Handle mouse upload file action."""
        if len(params) < 3:
            raise ValueError("Mouse upload file action requires x, y, and file path")
        x, y, file_path = float(params[0]), float(params[1]), params[2]
        mouse_upload_file(x, y, file_path)
        logger.info(f"Mouse uploaded file {file_path} at ({x}, {y})")
    
    def _handle_send_msg(self, params: List[str]):
        """Handle send message action."""
        if not params:
            raise ValueError("Send message action requires text")
        text = params[0]
        send_msg_to_user(text)
        logger.info(f"Sent message: {text}")
    
    def _handle_report_infeasible(self, params: List[str]):
        """Handle report infeasible action."""
        if not params:
            raise ValueError("Report infeasible action requires a reason")
        reason = params[0]
        report_infeasible(reason)
        logger.warning(f"Reported infeasible: {reason}")

    def _handle_get_bids(self, params: List[str]):
        """Handle get_bids action."""
        try:
            # First, let's check if BID.js is working by looking for data-testid attributes
            test_ids = self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[data-testid]');
                    const testIds = [];
                    elements.forEach(el => {
                        testIds.push(el.getAttribute('data-testid'));
                    });
                    return testIds;
                }
            """)
            
            logger.info(f"Found {len(test_ids)} elements with data-testid attributes: {test_ids[:10]}...")
            
            # Get all elements with data-testid attribute
            bids = self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[data-testid]');
                    const bidMap = {};
                    const inputElements = [];
                    const buttonElements = [];
                    const clickableElements = [];
                    
                    elements.forEach(el => {
                        const bid = el.getAttribute('data-testid');
                        const tagName = el.tagName.toLowerCase();
                        const text = el.textContent ? el.textContent.trim().substring(0, 50) : '';
                        const id = el.id || '';
                        const className = el.className || '';
                        const type = el.type || '';
                        const placeholder = el.placeholder || '';
                        const value = el.value || '';
                        const visible = el.offsetParent !== null;
                        const clickable = el.onclick || el.tagName === 'BUTTON' || el.tagName === 'A' || 
                                        el.getAttribute('role') === 'button' || 
                                        (typeof className === 'string' && (className.includes('button') || className.includes('btn')));
                        
                        const elementInfo = {
                            tag: tagName,
                            text: text,
                            id: id,
                            className: className,
                            type: type,
                            placeholder: placeholder,
                            value: value,
                            visible: visible,
                            clickable: clickable
                        };
                        
                        bidMap[bid] = elementInfo;
                        
                        // Categorize elements
                        if (tagName === 'input' || tagName === 'textarea') {
                            inputElements.push({bid: bid, ...elementInfo});
                        }
                        if (clickable) {
                            clickableElements.push({bid: bid, ...elementInfo});
                        }
                        if (tagName === 'button' || (typeof className === 'string' && (className.includes('button') || className.includes('btn')))) {
                            buttonElements.push({bid: bid, ...elementInfo});
                        }
                    });
                    
                    return {
                        all: bidMap,
                        inputs: inputElements,
                        buttons: buttonElements,
                        clickable: clickableElements,
                        total: elements.length
                    };
                }
            """)
            
            logger.info(f"Total elements with BIDs: {bids['total']}")
            logger.info(f"Input elements: {len(bids['inputs'])}")
            logger.info(f"Button elements: {len(bids['buttons'])}")
            logger.info(f"Clickable elements: {len(bids['clickable'])}")
            
            # Show input elements (likely search boxes)
            if bids['inputs']:
                logger.info("=== INPUT ELEMENTS ===")
                for elem in bids['inputs'][:10]:  # Show first 10
                    logger.info(f"BID: {elem['bid']} | Tag: {elem['tag']} | Type: {elem['type']} | Placeholder: {elem['placeholder']} | Text: {elem['text']}")
            
            # Show button elements
            if bids['buttons']:
                logger.info("=== BUTTON ELEMENTS ===")
                for elem in bids['buttons'][:10]:  # Show first 10
                    logger.info(f"BID: {elem['bid']} | Tag: {elem['tag']} | Text: {elem['text']} | Class: {elem['className']}")
            
            send_message_to_user(f"Found {bids['total']} elements with BIDs. Check logs for details.")
            
        except Exception as e:
            logger.error(f"Error getting BIDs: {e}")
            send_message_to_user(f"Error getting BIDs: {e}")
    
    def _handle_find_element(self, params: List[str]):
        """Handle find_element action to search for elements by properties."""
        if len(params) < 2:
            raise ValueError("find_element action requires property and value")
        
        property_name, value = params[0], params[1]
        
        try:
            elements = self.page.evaluate(f"""
                () => {{
                    const elements = document.querySelectorAll('[data-testid]');
                    const matches = [];
                    
                    elements.forEach(el => {{
                        const bid = el.getAttribute('data-testid');
                        let matchesProperty = false;
                        
                        switch('{property_name}') {{
                            case 'text':
                                matchesProperty = el.textContent && el.textContent.toLowerCase().includes('{value}'.toLowerCase());
                                break;
                            case 'placeholder':
                                matchesProperty = el.placeholder && el.placeholder.toLowerCase().includes('{value}'.toLowerCase());
                                break;
                            case 'type':
                                matchesProperty = el.type && el.type.toLowerCase() === '{value}'.toLowerCase();
                                break;
                            case 'tag':
                                matchesProperty = el.tagName.toLowerCase() === '{value}'.toLowerCase();
                                break;
                            case 'class':
                                matchesProperty = el.className && typeof el.className === 'string' && el.className.toLowerCase().includes('{value}'.toLowerCase());
                                break;
                            case 'id':
                                matchesProperty = el.id && el.id.toLowerCase().includes('{value}'.toLowerCase());
                                break;
                        }}
                        
                        if (matchesProperty) {{
                            matches.push({{
                                bid: bid,
                                tag: el.tagName.toLowerCase(),
                                text: el.textContent ? el.textContent.trim().substring(0, 50) : '',
                                id: el.id || '',
                                className: el.className || '',
                                type: el.type || '',
                                placeholder: el.placeholder || '',
                                visible: el.offsetParent !== null
                            }});
                        }}
                    }});
                    
                    return matches;
                }}
            """)
            
            if elements:
                logger.info(f"Found {len(elements)} elements matching {property_name}='{value}':")
                for elem in elements:
                    logger.info(f"BID: {elem['bid']} | Tag: {elem['tag']} | Text: {elem['text']} | Type: {elem['type']} | Placeholder: {elem['placeholder']}")
                send_message_to_user(f"Found {len(elements)} elements matching {property_name}='{value}'. Check logs for BIDs.")
            else:
                logger.info(f"No elements found matching {property_name}='{value}'")
                send_message_to_user(f"No elements found matching {property_name}='{value}'")
                
        except Exception as e:
            logger.error(f"Error finding elements: {e}")
            send_message_to_user(f"Error finding elements: {e}")

    def _handle_test_bid(self, params: List[str]):
        """Handle test_bid action to test if BID elements can be found."""
        if not params:
            raise ValueError("test_bid action requires a BID parameter")
        
        bid = params[0]
        try:
            # Try to find element using Playwright's get_by_test_id
            element = self.page.get_by_test_id(bid)
            count = element.count()
            
            if count > 0:
                logger.info(f"✅ Found element with BID '{bid}' using get_by_test_id (count: {count})")
                
                # Try to get element info
                try:
                    element_info = self.page.evaluate(f"""
                        () => {{
                            const el = document.querySelector('[data-testid="{bid}"]');
                            if (el) {{
                                return {{
                                    tag: el.tagName.toLowerCase(),
                                    text: el.textContent ? el.textContent.trim().substring(0, 50) : '',
                                    id: el.id || '',
                                    className: el.className || '',
                                    type: el.type || '',
                                    placeholder: el.placeholder || '',
                                    visible: el.offsetParent !== null
                                }};
                            }}
                            return null;
                        }}
                    """)
                    
                    if element_info:
                        logger.info(f"Element info: {element_info}")
                    else:
                        logger.info("Could not get element info")
                        
                except Exception as e:
                    logger.error(f"Error getting element info: {e}")
                
                send_message_to_user(f"✅ Found element with BID '{bid}'")
            else:
                logger.error(f"❌ Element with BID '{bid}' not found using get_by_test_id")
                send_message_to_user(f"❌ Element with BID '{bid}' not found")
                
        except Exception as e:
            logger.error(f"Error testing BID '{bid}': {e}")
            send_message_to_user(f"Error testing BID '{bid}': {e}")

    def _handle_direct_fill(self, params: List[str]):
        """Handle direct_fill action using Playwright directly."""
        if len(params) < 2:
            raise ValueError("direct_fill action requires BID and value parameters")
        
        bid, value = params[0], params[1]
        try:
            # Use Playwright directly to find and fill the element
            element = self.page.get_by_test_id(bid)
            count = element.count()
            
            if count > 0:
                logger.info(f"✅ Found element with BID '{bid}' for direct fill")
                
                # Try to fill the element directly
                element.fill(value)
                logger.info(f"✅ Successfully filled element '{bid}' with '{value}'")
                send_message_to_user(f"✅ Successfully filled element '{bid}' with '{value}'")
            else:
                logger.error(f"❌ Element with BID '{bid}' not found for direct fill")
                send_message_to_user(f"❌ Element with BID '{bid}' not found")
                
        except Exception as e:
            logger.error(f"Error in direct_fill for BID '{bid}': {e}")
            send_message_to_user(f"Error in direct_fill for BID '{bid}': {e}")
    
    def _handle_direct_click(self, params: List[str]):
        """Handle direct_click action using Playwright directly."""
        if not params:
            raise ValueError("direct_click action requires a BID parameter")
        
        bid = params[0]
        try:
            # Use Playwright directly to find and click the element
            element = self.page.get_by_test_id(bid)
            count = element.count()
            
            if count > 0:
                logger.info(f"✅ Found element with BID '{bid}' for direct click")
                
                # Try to click the element directly
                element.click()
                logger.info(f"✅ Successfully clicked element '{bid}'")
                send_message_to_user(f"✅ Successfully clicked element '{bid}'")
            else:
                logger.error(f"❌ Element with BID '{bid}' not found for direct click")
                send_message_to_user(f"❌ Element with BID '{bid}' not found")
                
        except Exception as e:
            logger.error(f"Error in direct_click for BID '{bid}': {e}")
            send_message_to_user(f"Error in direct_click for BID '{bid}': {e}")

    def _handle_direct_press(self, params: List[str]):
        """Handle direct_press action using Playwright directly."""
        if len(params) < 2:
            raise ValueError("direct_press action requires BID and key parameters")
        
        bid, key = params[0], params[1]
        try:
            # Use Playwright directly to find and press key on the element
            element = self.page.get_by_test_id(bid)
            count = element.count()
            
            if count > 0:
                logger.info(f"✅ Found element with BID '{bid}' for direct press")
                
                # Try to press the key on the element
                element.press(key)
                logger.info(f"✅ Successfully pressed '{key}' on element '{bid}'")
                send_message_to_user(f"✅ Successfully pressed '{key}' on element '{bid}'")
            else:
                logger.error(f"❌ Element with BID '{bid}' not found for direct press")
                send_message_to_user(f"❌ Element with BID '{bid}' not found")
                
        except Exception as e:
            logger.error(f"Error in direct_press for BID '{bid}': {e}")
            send_message_to_user(f"Error in direct_press for BID '{bid}': {e}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="BrowserGym Actions Runner using bgym_utils",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py sample_actions.txt
  python main.py sample_actions.txt --headless
  python main.py sample_actions.txt --browser firefox
  python main.py sample_actions.txt --verbose
        """
    )
    
    parser.add_argument(
        "actions_file",
        nargs='?',
        default="sample_actions.txt",
        help="Path to the BrowserGym actions file (default: sample_actions.txt)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser to use (default: chromium)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--output-dir",
        default="screenshots",
        help="Directory for screenshots and outputs (default: screenshots)"
    )
    
    args = parser.parse_args()
    
    # Validate actions file
    actions_file = Path(args.actions_file)
    if not actions_file.exists():
        print(f"Error: Actions file not found: {actions_file}")
        sys.exit(1)
    
    # Set up logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"BrowserGym Actions Runner (bgym_utils)")
    print(f"Actions file: {actions_file}")
    print(f"Browser: {args.browser}")
    print(f"Headless: {args.headless}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    # Initialize and run
    runner = BrowserGymRunner(
        headless=args.headless,
        browser_type=args.browser
    )
    
    try:
        # Run the actions
        results = runner.run_actions_file(str(actions_file))
        
        # Print results
        print("\n" + "="*50)
        print("EXECUTION RESULTS")
        print("="*50)
        print(f"Total actions: {results['total_actions']}")
        print(f"Successful: {results['successful_actions']}")
        print(f"Failed: {results['failed_actions']}")
        print(f"Execution time: {results['execution_time']:.2f} seconds")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  Line {error['line']}: {error['action']} - {error['error']}")
        
        # Exit with appropriate code
        if results['failed_actions'] > 0:
            print(f"\n❌ {results['failed_actions']} action(s) failed")
            sys.exit(1)
        else:
            print(f"\n✅ All actions completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        runner.cleanup()


if __name__ == "__main__":
    main()

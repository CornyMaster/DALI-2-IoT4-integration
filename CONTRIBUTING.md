# Contributing to the Lunatone DALI-2 IoT4 Gateway Integration

Thank you for your interest in contributing to this Home Assistant integration!

## Development Setup

### Prerequisites

- Home Assistant development environment
- Python 3.11 or later
- Lunatone DALI-2 IoT or IoT4 gateway for testing

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/CornyMaster/DALI-2-IoT4-integration.git
   cd DALI-2-IoT4-integration
   ```

2. Create a symbolic link in your Home Assistant config:
   ```bash
   cd /path/to/homeassistant/config/custom_components
   ln -s /path/to/DALI-2-IoT4-integration/custom_components/lunatone_dali2_iot4 lunatone_dali2_iot4
   ```

3. Restart Home Assistant

4. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.lunatone_dali2_iot4: debug
   ```

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for function parameters and return values
- Include docstrings for all public functions and classes
- Keep lines under 100 characters when possible

## Testing

Before submitting a pull request:

1. **Validate Python syntax:**
   ```bash
   python -m py_compile custom_components/lunatone_dali2_iot4/*.py
   ```

2. **Test with your Home Assistant instance:**
   - Install the integration
   - Verify all platforms load (light, binary_sensor, sensor)
   - Test basic functionality (lights, buttons, sensors)
   - Check logs for errors

3. **Test edge cases:**
   - Connection loss and reconnection
   - Invalid device addresses
   - Empty DALI bus
   - Multiple devices of same type

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write clear, concise commit messages
   - Update documentation if needed
   - Add comments for complex logic

3. **Update CHANGELOG.md:**
   - Add entry under `[Unreleased]` section
   - Categorize as: Added, Changed, Fixed, Removed

4. **Submit pull request:**
   - Provide clear description of changes
   - Reference any related issues
   - Include testing details

5. **Wait for review:**
   - Address any feedback
   - Update PR as needed

## Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:

- Integration version
- Home Assistant version
- Gateway firmware version
- Detailed steps to reproduce
- Relevant log output with debug logging enabled

## Suggesting Features

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml) and include:

- Clear description of the feature
- Use case and benefits
- Any alternative solutions considered

## Code of Conduct

- Be respectful and constructive
- Help others learn and grow
- Focus on what's best for the community
- Accept constructive criticism gracefully

## Project Structure

```
custom_components/lunatone_dali2_iot4/
├── __init__.py           # Integration setup, services
├── manifest.json         # Integration metadata
├── strings.json          # Translation strings
├── config_flow.py        # Configuration UI
├── const.py              # Constants and DALI commands
├── coordinator.py        # Update coordinator
├── light.py              # Light platform
├── binary_sensor.py      # Binary sensor platform
├── sensor.py             # Sensor platform
├── lunatone_api.py       # WebSocket API client
├── storage.py            # Device persistence
├── repairs.py            # Repair flow
└── services.yaml         # Service definitions
```

## Key Areas for Contribution

- **Device Support:** Testing with different DALI device types
- **Documentation:** Improving guides and examples
- **Bug Fixes:** Addressing reported issues
- **Features:** New functionality (scenes, advanced RGB, etc.)
- **Testing:** Automated tests and validation
- **Translations:** Multi-language support

## Questions?

- Open a [GitHub Discussion](https://github.com/CornyMaster/DALI-2-IoT4-integration/discussions)
- Ask in [Home Assistant Community](https://community.home-assistant.io/)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

# Contributing to Will I Fly PUW

First off, thank you for considering contributing to Will I Fly PUW! It's people like you that make this tool better for travelers in the Palouse region.

## Code of Conduct

This project and everyone participating in it is governed by a simple principle: be respectful, be constructive, and help make air travel less stressful.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (flight numbers, dates, weather conditions)
- **Describe the behavior you observed** and what you expected
- **Include screenshots** if relevant
- **Mention your browser/environment** (Chrome 120, Safari 17, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any alternative solutions** you've considered

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Make your changes**:
   - Follow the existing code style
   - Add tests if applicable
   - Update documentation as needed
3. **Test thoroughly**:
   - Ensure backend tests pass: `cd backend && pytest`
   - Test frontend locally: `cd frontend && npm run dev`
4. **Commit with clear messages**:
   ```
   feat: add SMS notifications for high-risk flights
   fix: correct crosswind calculation for runway 23
   docs: update API endpoint documentation
   ```
5. **Push to your fork** and submit a pull request

## Development Setup

See the main [README.md](README.md) for detailed setup instructions.

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn api:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if available)
cd frontend
npm test
```

## Style Guidelines

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where appropriate
- Document functions with docstrings
- Keep functions focused and under 50 lines when possible

### JavaScript/React (Frontend)

- Use functional components with hooks
- Follow React best practices
- Use meaningful variable names
- Keep components small and focused

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests when relevant

## Project Structure

```
kpuw_tracker/
├── backend/              # FastAPI backend
│   ├── api.py           # Main API endpoints
│   ├── flight_data.py   # Flight data management
│   ├── prediction_engine.py  # Risk calculations
│   └── weather_data.py  # Weather integration
├── frontend/            # React frontend
│   └── src/
│       ├── App.jsx      # Main application
│       └── components/  # React components
└── README.md
```

## Priority Areas for Contribution

We're especially looking for help with:

1. **Prediction Accuracy**: Improving the risk calculation algorithm
2. **Testing**: Adding comprehensive test coverage
3. **Mobile Experience**: Optimizing the mobile interface
4. **Documentation**: Improving setup guides and API docs
5. **Performance**: Optimizing database queries and API response times

## Questions?

Feel free to open an issue with the `question` label if you need clarification on anything.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

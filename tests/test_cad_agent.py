"""
Tests for CAD Generation Agent.
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path

from cad_agent import CadAgent


class TestCadAgentInit:
    """Test CadAgent initialization."""
    
    def test_agent_creation(self):
        """Test CadAgent can be created."""
        agent = CadAgent()
        assert agent is not None
        assert hasattr(agent, 'client')
        print("CadAgent initialized successfully")
    
    def test_agent_with_callbacks(self):
        """Test CadAgent with thought/status callbacks."""
        thoughts = []
        statuses = []
        
        def on_thought(text):
            thoughts.append(text)
        
        def on_status(status):
            statuses.append(status)
        
        agent = CadAgent(on_thought=on_thought, on_status=on_status)
        assert agent.on_thought is not None
        assert agent.on_status is not None


class TestCadGeneration:
    """Test CAD generation (requires API key)."""
    
    @pytest.fixture
    def agent(self):
        """Create a CadAgent instance."""
        return CadAgent()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set"
    )
    async def test_generate_simple_cube(self, agent):
        """Test generating a simple cube."""
        thoughts = []
        statuses = []
        
        agent.on_thought = lambda t: thoughts.append(t)
        agent.on_status = lambda s: statuses.append(s)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cad_dir = os.path.join(temp_dir, "cad")
            os.makedirs(cad_dir)
            try:
                result = await agent.generate_prototype("A simple 10mm cube", output_dir=cad_dir)
                print(f"Generation result: {result}")
                print(f"Thoughts received: {len(thoughts)}")
                print(f"Statuses received: {len(statuses)}")

                # Check if STL was generated
                assert result is not None
                assert 'file_path' in result
                assert os.path.exists(result['file_path'])
            except Exception as e:
                pytest.fail(f"Generation failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set"
    )
    async def test_generate_sphere(self, agent):
        """Test generating a sphere."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cad_dir = os.path.join(temp_dir, "cad")
            os.makedirs(cad_dir)
            try:
                result = await agent.generate_prototype("A sphere with 25mm radius", output_dir=cad_dir)
                print(f"Sphere generation result: {result}")
                assert result is not None
                assert 'file_path' in result
                assert os.path.exists(result['file_path'])
            except Exception as e:
                pytest.fail(f"Sphere generation failed: {e}")


class TestCadIteration:
    """Test CAD iteration (modifying existing designs)."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set"
    )
    async def test_iterate_prototype(self):
        """Test iterating on an existing design."""
        agent = CadAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cad_dir = os.path.join(temp_dir, "cad")
            os.makedirs(cad_dir)
            # Create a dummy current_design.py for iteration
            design_file = os.path.join(cad_dir, "current_design.py")
            with open(design_file, "w") as f:
                f.write("from build123d import *; result_part = Box(10, 10, 10); export_stl(result_part, 'output.stl')")

            try:
                result = await agent.iterate_prototype("Make it 50% larger", output_dir=cad_dir)
                print(f"Iteration result: {result}")
                assert result is not None
                assert 'file_path' in result
                assert os.path.exists(result['file_path'])
            except Exception as e:
                pytest.fail(f"Iteration failed: {e}")


class TestCadSystemPrompt:
    """Test CAD agent system prompt configuration."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        agent = CadAgent()
        # The agent should have a system prompt for Gemini
        assert hasattr(agent, 'system_instruction')


class TestBuild123dImport:
    """Test build123d availability."""
    
    def test_build123d_import(self):
        """Test if build123d is installed."""
        try:
            import build123d
            print(f"build123d version: {build123d.__version__}")
        except ImportError:
            pytest.skip("build123d not installed")

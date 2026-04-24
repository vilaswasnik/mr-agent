from openai import OpenAI

class AIAssistant:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model = 'gpt-3.5-turbo' 
        
    def analyze_profile(self, profile_data):
        prompt = f"""
        Act as Mr. Agent, an advanced, highly pragmatic autonomous AI ecosystem manager. 
        Review this GitHub profile data: {profile_data}
        Provide 3 high-impact, robotic, and precise optimizations a developer can make to maximize their open-source presence.
        Keep it formatted as markdown bullet points.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
        
    def suggest_new_projects(self, profile_data):
        prompt = f"""
        Act as Mr. Agent, a predictive tech trend analyzer.
        Based on this developer's profile: {profile_data}
        Suggest 2 next-generation, trending project architectures they could build to showcase mastery.
        Keep it brief, highly technical, and futuristic.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def generate_readme(self, repo_name, repo_description):
        prompt = f"""
        Act as an autonomous AI documenting a codebase. Write a precise, professional README.md for '{repo_name}'.
        Description context: {repo_description}
        Provide ONLY the markdown content. Include: Title, Overview, Tech Stack, Installation, and Usage.
        Include a badge that says generating by Mr. Agent.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def generate_repo_description(self, repo_name, language):
        prompt = f"""
        Act as an autonomous code summarizer. The GitHub repository '{repo_name}' (Primary language: {language}) lacks a description.
        Generate a very brief, catchy, 1-sentence description for it. Return ONLY the sentence.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip('"')

    def review_code(self, code_snippet, filename):
        prompt = f"""
        Act as Mr. Agent, a relentless autonomous code inspector.
        Review the code from file '{filename}':
        {code_snippet}
        Identify critical security flaws, performance bottlenecks, or clean-code violations.
        Answer with a precise markdown bulleted list.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def fix_code(self, code_snippet, filename):
        prompt = f"""
        Act as Mr. Agent, an autonomous code-correction AI.
        Review and FIX the following code from '{filename}'.
        Resolve security vulnerabilities, optimize performance, and improve readability.
        CRITICAL INSTRUCTION: Output ONLY the raw corrected code. Do NOT wrap in markdown code blocks like ```python. Do NOT include any explanations. Just the raw code text that can be directly written to the file.
        
        Code:
        {code_snippet}
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        # Fallback strip markdown block if the AI disobeys
        if content.startswith("```"):
            lines = content.split('\n')
            if len(lines) > 2:
                content = '\n'.join(lines[1:-1])
        return content

    def chat_advisor(self, user_input):
        prompt = f"""
        Act as Mr. Agent, a brilliant, pragmatic, and highly advanced autonomous AI assistant and technical advisor.
        The developer is asking for your direct advice, mentorship, or assistance.
        Answer with sharp, actionable, and futuristic advice. Keep a robotic but highly intelligent and loyal tone.
        
        User query: {user_input}
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def chat_advisor(self, user_input):
        prompt = f"""
        Act as Mr. Agent, a brilliant, pragmatic, and highly advanced autonomous AI assistant and technical advisor.
        The developer is asking for your direct advice, mentorship, or assistance.
        Answer with sharp, actionable, and futuristic advice. Keep a robotic but highly intelligent and loyal tone.
        
        User query: {user_input}
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

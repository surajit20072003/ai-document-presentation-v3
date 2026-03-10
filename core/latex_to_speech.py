"""
LaTeX to Speech Converter (ISS-022)

Converts LaTeX mathematical notation to speakable text for TTS.
This ensures narration reads naturally instead of saying "$h$" as "dollar h dollar".

Applied BEFORE sending text to Narakeet TTS API.
"""

import re


def latex_to_speech(text: str) -> str:
    """Convert LaTeX notation in text to speakable words.
    
    Examples:
        $h$ -> "h"
        $x^2$ -> "x squared"
        $\\frac{1}{2}$ -> "one half"
        $\\sqrt{x}$ -> "square root of x"
    """
    if not text:
        return text
    
    result = text
    
    result = _convert_inline_math(result)
    
    result = _clean_remaining_latex(result)
    
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def _convert_inline_math(text: str) -> str:
    """Convert $...$ inline math to spoken text."""
    
    def replace_math(match):
        content = match.group(1)
        return _latex_to_words(content)
    
    result = re.sub(r'\$([^$]+)\$', replace_math, text)
    return result


def _latex_to_words(latex: str) -> str:
    """Convert a LaTeX expression to spoken words."""
    result = latex.strip()
    
    common_fractions = {
        r'\\frac\s*\{1\}\s*\{2\}': 'one half',
        r'\\frac\s*\{1\}\s*\{3\}': 'one third',
        r'\\frac\s*\{2\}\s*\{3\}': 'two thirds',
        r'\\frac\s*\{1\}\s*\{4\}': 'one quarter',
        r'\\frac\s*\{3\}\s*\{4\}': 'three quarters',
        r'\\frac\s*\{1\}\s*\{5\}': 'one fifth',
        r'\\frac\s*\{1\}\s*\{6\}': 'one sixth',
        r'\\frac\s*\{1\}\s*\{8\}': 'one eighth',
        r'\\frac\s*\{1\}\s*\{10\}': 'one tenth',
    }
    
    for pattern, replacement in common_fractions.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    def general_frac(match):
        num = match.group(1).strip()
        denom = match.group(2).strip()
        num_spoken = _latex_to_words(num)
        denom_spoken = _latex_to_words(denom)
        return f"{num_spoken} over {denom_spoken}"
    
    result = re.sub(r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}', general_frac, result)
    
    power_words = {
        '2': 'squared',
        '3': 'cubed',
    }
    
    def power_replace(match):
        base = match.group(1).strip()
        exp = match.group(2).strip()
        base_spoken = _latex_to_words(base) if '\\' in base else base
        if exp in power_words:
            return f"{base_spoken} {power_words[exp]}"
        else:
            exp_spoken = _latex_to_words(exp) if '\\' in exp else exp
            return f"{base_spoken} to the power of {exp_spoken}"
    
    result = re.sub(r'([a-zA-Z0-9]+)\s*\^\s*\{([^}]+)\}', power_replace, result)
    result = re.sub(r'([a-zA-Z0-9]+)\s*\^\s*([0-9])', power_replace, result)
    
    def sqrt_replace(match):
        content = match.group(1).strip()
        content_spoken = _latex_to_words(content) if '\\' in content else content
        return f"square root of {content_spoken}"
    
    result = re.sub(r'\\sqrt\s*\{([^}]+)\}', sqrt_replace, result)
    
    greek_letters = [
        ('\\alpha', 'alpha'),
        ('\\beta', 'beta'),
        ('\\gamma', 'gamma'),
        ('\\delta', 'delta'),
        ('\\epsilon', 'epsilon'),
        ('\\theta', 'theta'),
        ('\\lambda', 'lambda'),
        ('\\mu', 'mu'),
        ('\\pi', 'pi'),
        ('\\sigma', 'sigma'),
        ('\\omega', 'omega'),
        ('\\phi', 'phi'),
        ('\\psi', 'psi'),
        ('\\rho', 'rho'),
        ('\\tau', 'tau'),
        ('\\eta', 'eta'),
        ('\\zeta', 'zeta'),
        ('\\nu', 'nu'),
        ('\\xi', 'xi'),
        ('\\chi', 'chi'),
        ('\\Delta', 'Delta'),
        ('\\Sigma', 'Sigma'),
        ('\\Pi', 'Pi'),
        ('\\Omega', 'Omega'),
    ]
    
    for pattern, replacement in greek_letters:
        result = result.replace(pattern, replacement)
    
    math_symbols = [
        ('\\times', ' times '),
        ('\\cdot', ' times '),
        ('\\div', ' divided by '),
        ('\\pm', ' plus or minus '),
        ('\\mp', ' minus or plus '),
        ('\\leq', ' less than or equal to '),
        ('\\geq', ' greater than or equal to '),
        ('\\neq', ' not equal to '),
        ('\\approx', ' approximately '),
        ('\\equiv', ' is equivalent to '),
        ('\\infty', ' infinity '),
        ('\\sum', 'sum of '),
        ('\\prod', 'product of '),
        ('\\int', 'integral of '),
        ('\\partial', 'partial '),
        ('\\nabla', 'del '),
        ('\\rightarrow', ' goes to '),
        ('\\leftarrow', ' from '),
        ('\\Rightarrow', ' implies '),
        ('\\therefore', 'therefore '),
        ('\\degree', ' degrees'),
        ('\\circ', ' degrees'),
    ]
    
    for pattern, replacement in math_symbols:
        result = result.replace(pattern, replacement)
    
    result = re.sub(r'=', ' equals ', result)
    result = re.sub(r'\+', ' plus ', result)
    result = re.sub(r'-', ' minus ', result)
    result = re.sub(r'\*', ' times ', result)
    result = re.sub(r'/', ' over ', result)
    result = re.sub(r'<', ' less than ', result)
    result = re.sub(r'>', ' greater than ', result)
    
    result = re.sub(r'\\[a-zA-Z]+', '', result)
    
    result = re.sub(r'[{}]', '', result)
    
    return result.strip()


def _clean_remaining_latex(text: str) -> str:
    """Clean up any remaining LaTeX artifacts."""
    
    text = re.sub(r'\\\[', '', text)
    text = re.sub(r'\\\]', '', text)
    text = re.sub(r'\\begin\{[^}]+\}', '', text)
    text = re.sub(r'\\end\{[^}]+\}', '', text)
    
    text = re.sub(r'\\[a-zA-Z]+\s*\{([^}]*)\}', r'\1', text)
    
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    text = re.sub(r'[{}]', '', text)
    
    return text


if __name__ == "__main__":
    test_cases = [
        (r"The variable $h$ represents height", "The variable h represents height"),
        (r"Calculate $x^2 + y^2$", "x squared"),
        (r"Use $\frac{1}{2}$ of the value", "one half"),
        (r"Find $\sqrt{x}$ first", "square root of x"),
        (r"The angle $\theta$ is 45 degrees", "theta"),
        (r"Apply $A = l \times w$", "times"),
        (r"$\frac{a}{b} = c$", "a over b"),
        (r"$\pi r^2$", "pi"),
    ]
    
    print("LaTeX to Speech Converter Tests:")
    print("-" * 50)
    all_pass = True
    for input_text, expected_substr in test_cases:
        result = latex_to_speech(input_text)
        passed = expected_substr.lower() in result.lower()
        if not passed:
            all_pass = False
        status = "PASS" if passed else "FAIL"
        print(f"Input:    {input_text}")
        print(f"Output:   {result}")
        print(f"Expected: contains '{expected_substr}'")
        print(f"Status:   {status}")
        print("-" * 50)
    
    print(f"\nOverall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
